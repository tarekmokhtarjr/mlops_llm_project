
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import math
import os
import re
import statistics
import time
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

import mlflow
from dotenv import load_dotenv
from openai import AsyncOpenAI
from ragas.embeddings import embedding_factory
from ragas.llms import llm_factory
from ragas.metrics.collections import (
    AnswerCorrectness,
    AnswerRelevancy,
    ContextPrecision,
    ContextRecall,
    Faithfulness,
)

from app.clients.vector_db_client import VectorDBClientWrapper
from app.models.chat import ChatBotLlmModel
from app.models.embedding import EmbeddingModel
from app.models.guard import GuardModel
from app.services.rag import RAG


load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

RAGAS_METRIC_NAMES = (
    "faithfulness",
    "answer_relevancy",
    "answer_correctness",
    "context_precision",
    "context_recall",
)

RETRIEVAL_METRIC_NAMES = (
    "hit_rate",
    "precision_at_k",
    "recall_at_k",
    "mrr",
)

METRIC_NAMES = RAGAS_METRIC_NAMES + RETRIEVAL_METRIC_NAMES


# ============================================================
# Version and environment helpers
# ============================================================

def package_version(package_name: str) -> str:
    try:
        return version(package_name)
    except PackageNotFoundError:
        return "unknown"


def env_value(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def env_enabled(name: str, default: str = "false") -> bool:
    return env_value(name, default).lower() in {
        "1", "true", "yes", "on"
    }


# ============================================================
# Optional Langfuse integration
# ============================================================

def get_langfuse_client() -> Any | None:
    """Return a Langfuse v4 client when tracing is enabled."""

    if not env_enabled("LANGFUSE_ENABLED"):
        logger.info("Langfuse tracing is disabled.")
        return None

    required = (
        "LANGFUSE_PUBLIC_KEY",
        "LANGFUSE_SECRET_KEY",
        "LANGFUSE_BASE_URL",
    )
    missing = [key for key in required if not env_value(key)]

    if missing:
        logger.warning(
            "Langfuse is enabled but configuration is incomplete; "
            "missing: %s. Continuing without Langfuse.",
            ", ".join(missing),
        )
        return None

    try:
        from langfuse import get_client

        return get_client()
    except Exception:
        logger.exception(
            "Could not initialize Langfuse; continuing without tracing."
        )
        return None


def flush_langfuse(client: Any | None) -> None:
    if client is None:
        return

    try:
        client.flush()
        logger.info("Flushed pending Langfuse events.")
    except Exception:
        logger.exception("Failed to flush Langfuse events.")


def score_langfuse_trace(
    client: Any,
    result: dict[str, Any],
) -> None:
    """
    Add numeric RAGAS and retrieval scores to the active Langfuse trace.
    Failures in observability must not fail the evaluation itself.
    """

    for metric_name in METRIC_NAMES:
        value = result.get(metric_name)

        if not isinstance(value, (int, float)):
            continue

        if not math.isfinite(float(value)):
            continue

        try:
            client.score_current_trace(
                name=metric_name,
                value=float(value),
                data_type="NUMERIC",
                comment=f"Automated evaluation: {metric_name}",
                metadata={
                    "evaluator": "RAGAS",
                    "dataset_case_id": str(result["id"]),
                },
            )
        except Exception:
            logger.exception(
                "Could not send score %s for case %s to Langfuse.",
                metric_name,
                result.get("id"),
            )


# ============================================================
# Dataset loading
# ============================================================

def load_dataset(path: Path) -> list[dict[str, Any]]:
    """
    Accept a JSON array, a {"data": [...]} JSON object, or JSONL.

    Required fields:
      id, question, reference, relevant_document_ids
    """

    raw = path.read_text(encoding="utf-8").strip()

    if not raw:
        raise ValueError(f"Dataset is empty: {path}")

    try:
        parsed = json.loads(raw)

        if isinstance(parsed, dict):
            parsed = parsed.get("data", [parsed])

        if not isinstance(parsed, list):
            raise ValueError(
                "Dataset JSON must be an array or an object "
                "containing a 'data' array."
            )

        records = parsed

    except json.JSONDecodeError:
        records = [
            json.loads(line)
            for line in raw.splitlines()
            if line.strip()
        ]

    if not records:
        raise ValueError(f"No records found in dataset: {path}")

    required = {
        "id",
        "question",
        "reference",
        "relevant_document_ids",
    }
    seen_ids: set[str] = set()

    for index, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            raise ValueError(f"Record {index} must be a JSON object.")

        missing = required - record.keys()
        if missing:
            raise ValueError(
                f"Record {index} is missing fields: {sorted(missing)}"
            )

        record_id = str(record["id"])
        if record_id in seen_ids:
            raise ValueError(f"Duplicate dataset ID: {record_id}")
        seen_ids.add(record_id)

        if not str(record["question"]).strip():
            raise ValueError(f"Empty question in record {record_id}.")

        if not str(record["reference"]).strip():
            raise ValueError(f"Empty reference in record {record_id}.")

        if not isinstance(record["relevant_document_ids"], list):
            raise ValueError(
                "relevant_document_ids must be a list in record "
                f"{record_id}."
            )

    return records


# ============================================================
# Build the existing RAG application
# ============================================================

def build_rag(top_k: int) -> RAG:
    qdrant_url = env_value("QDRANT_URL")

    if not qdrant_url:
        qdrant_host = env_value("QDRANT_HOST", "qdrant")
        qdrant_port = env_value("QDRANT_PORT", "6333")
        qdrant_url = f"http://{qdrant_host}:{qdrant_port}"

    collection = env_value(
        "QDRANT_COLLECTION",
        "test_qwen_embeddings",
    )

    vector_db = VectorDBClientWrapper(
        url=qdrant_url,
        collection_name=collection,
        api_key=env_value("QDRANT_API_KEY") or None,
    )

    return RAG(
        embedding_model=EmbeddingModel(),
        vector_db=vector_db,
        guard_model=GuardModel(),
        chat_model=ChatBotLlmModel(),
        retrieval_limit=top_k,
    )


def endpoint_url(
    server_env: str,
    port_env: str,
    default_server: str,
) -> str:
    server = env_value(server_env, default_server).rstrip("/")
    port = env_value(port_env, "8000")

    # Support either a hostname or a URL already containing a port.
    if re.search(r":\d+$", server):
        return f"{server}/v1"

    return f"{server}:{port}/v1"


def build_metrics() -> tuple[list[Any], list[AsyncOpenAI]]:
    """Build RAGAS 0.4.x collection metrics using the vLLM endpoints."""

    judge_model = env_value(
        "CHATBOT_MODEL",
        "Qwen/Qwen2.5-0.5B-Instruct",
    )
    judge_url = endpoint_url(
        "CHATBOT_SERVER",
        "CHATBOT_SERVER_PORT",
        "http://llm",
    )
    judge_key = env_value("CHATBOT_API_KEY", "dumb")

    embedding_model = env_value(
        "EMBEDDING_MODEL",
        "Qwen/Qwen3-Embedding-0.6B",
    )
    embedding_url = endpoint_url(
        "EMBEDDING_MODEL_SERVER",
        "EMBEDDING_MODEL_SERVER_PORT",
        "http://embedding",
    )
    embedding_key = env_value("EMBEDDING_MODEL_API_KEY", "dumb")

    judge_client = AsyncOpenAI(
        base_url=judge_url,
        api_key=judge_key,
    )
    embedding_client = AsyncOpenAI(
        base_url=embedding_url,
        api_key=embedding_key,
    )

    judge_llm = llm_factory(
        judge_model,
        client=judge_client,
        max_tokens=2048,
    )
    judge_embeddings = embedding_factory(
        provider="openai",
        model=embedding_model,
        client=embedding_client,
    )

    metrics = [
        Faithfulness(llm=judge_llm),
        AnswerRelevancy(
            llm=judge_llm,
            embeddings=judge_embeddings,
        ),
        AnswerCorrectness(
            llm=judge_llm,
            embeddings=judge_embeddings,
        ),
        ContextPrecision(llm=judge_llm),
        ContextRecall(llm=judge_llm),
    ]

    return metrics, [judge_client, embedding_client]


# ============================================================
# Retrieved-document helpers
# ============================================================

def get_payload(document: Any) -> dict[str, Any]:
    payload = getattr(document, "payload", None)
    return payload if isinstance(payload, dict) else {}


def document_text(document: Any) -> str:
    """Format a Qdrant payload as text for RAGAS."""

    payload = get_payload(document)

    return "\n".join(
        [
            f"Article: {payload.get('law_number', '')}",
            f"Legal hierarchy: {payload.get('title', '')}",
            f"Text: {payload.get('content', '')}",
        ]
    ).strip()


def document_identifiers(document: Any) -> set[str]:
    """Return the Qdrant point ID and article-number identifiers."""

    identifiers: set[str] = set()
    point_id = getattr(document, "id", None)

    if point_id is not None:
        identifiers.add(str(point_id).strip())

    law_number = str(
        get_payload(document).get("law_number", "")
    ).strip()

    if law_number:
        identifiers.add(law_number)

        # Normalize Arabic-Indic digits to Western digits.
        normalized = law_number.translate(
            str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
        )
        article_match = re.search(r"\d+", normalized)

        if article_match:
            identifiers.add(article_match.group())

    return identifiers


def normalize_reference_id(value: Any) -> str:
    value = str(value).strip()

    if re.fullmatch(r"[٠-٩]+", value):
        return value.translate(
            str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
        )

    return value


# ============================================================
# Retrieval metrics
# ============================================================

def calculate_retrieval_metrics(
    retrieved_documents: list[Any],
    relevant_ids: list[Any],
) -> dict[str, float | None]:
    """
    ID-based metrics.

    The dataset's relevant_document_ids must match Qdrant point IDs
    or article identifiers. If IDs are not annotated, scores are None.
    """

    expected = {
        normalize_reference_id(value)
        for value in relevant_ids
    }

    if not expected:
        return {
            "hit_rate": None,
            "precision_at_k": None,
            "recall_at_k": None,
            "mrr": None,
        }

    ranked_ids = [
        {
            normalize_reference_id(identifier)
            for identifier in document_identifiers(document)
        }
        for document in retrieved_documents
    ]

    relevant_flags = [
        bool(identifiers & expected)
        for identifiers in ranked_ids
    ]

    hits = sum(relevant_flags)
    retrieved_count = len(ranked_ids)

    first_relevant_rank = next(
        (
            rank
            for rank, is_relevant in enumerate(relevant_flags, start=1)
            if is_relevant
        ),
        None,
    )

    return {
        "hit_rate": float(hits > 0),
        "precision_at_k": (
            hits / retrieved_count if retrieved_count else 0.0
        ),
        "recall_at_k": hits / len(expected),
        "mrr": (
            1.0 / first_relevant_rank
            if first_relevant_rank is not None
            else 0.0
        ),
    }


# ============================================================
# Generate an answer from the same retrieval result
# ============================================================

def generate_from_retrieval(
    rag: RAG,
    question: str,
    retrieval: Any,
) -> str:
    """
    Generate from an existing retrieval result.

    This avoids calling rag.answer(question), which would retrieve again.
    """

    if not retrieval.accepted:
        return (
            retrieval.refusal_reason
            or "The request was rejected by a guard."
        )

    if not retrieval.results:
        return "لم يتم العثور على سياق قانوني مناسب للإجابة عن السؤال."

    context = rag._build_context(retrieval.results)
    prompt = rag._build_prompt(query=question, context=context)

    return rag.chat_model.invoke(prompt).strip()


# ============================================================
# One evaluation case
# ============================================================

def score_value(metric_result: Any) -> float | None:
    value = getattr(metric_result, "value", None)

    if value is None:
        return None

    value = float(value)
    return value if math.isfinite(value) else None


async def _evaluate_case(
    record: dict[str, Any],
    rag: RAG,
    metrics: list[Any],
    top_k: int,
) -> dict[str, Any]:
    question = str(record["question"])
    reference = str(record["reference"])
    started = time.perf_counter()

    # Retrieve exactly once; use the same documents for generation
    # and RAGAS context evaluation.
    retrieval = rag.retrieve_legal_documents(
        question,
        limit=top_k,
    )

    retrieved_documents = retrieval.results
    contexts = [
        document_text(document)
        for document in retrieved_documents
    ]

    answer = generate_from_retrieval(
        rag=rag,
        question=question,
        retrieval=retrieval,
    )

    result: dict[str, Any] = {
        "id": str(record["id"]),
        "question": question,
        "reference": reference,
        "answer": answer,
        "category": record.get("category"),
        "difficulty": record.get("difficulty"),
        "search_type": retrieval.search_type,
        "accepted": retrieval.accepted,
        "refusal_reason": retrieval.refusal_reason,
        "retrieved_documents": [
            {
                "id": str(getattr(document, "id", "")),
                "law_number": get_payload(document).get("law_number"),
                "title": get_payload(document).get("title"),
                "content": get_payload(document).get("content"),
                "score": getattr(document, "score", None),
            }
            for document in retrieved_documents
        ],
        "retrieved_contexts": contexts,
        "latency_seconds": round(
            time.perf_counter() - started,
            4,
        ),
    }

    result.update(
        calculate_retrieval_metrics(
            retrieved_documents=retrieved_documents,
            relevant_ids=record["relevant_document_ids"],
        )
    )

    if not contexts or not answer.strip():
        for name in RAGAS_METRIC_NAMES:
            result[name] = None

        result["metric_errors"] = {
            "evaluation": "No retrieved contexts or no generated answer."
        }
        return result

    metric_inputs = {
        "faithfulness": {
            "user_input": question,
            "response": answer,
            "retrieved_contexts": contexts,
        },
        "answer_relevancy": {
            "user_input": question,
            "response": answer,
        },
        "answer_correctness": {
            "user_input": question,
            "response": answer,
            "reference": reference,
        },
        "context_precision": {
            "user_input": question,
            "reference": reference,
            "retrieved_contexts": contexts,
        },
        "context_recall": {
            "user_input": question,
            "reference": reference,
            "retrieved_contexts": contexts,
        },
    }

    metric_errors: dict[str, str] = {}

    for metric in metrics:
        name = metric.name

        try:
            metric_result = await metric.ascore(**metric_inputs[name])
            result[name] = score_value(metric_result)

            reason = getattr(metric_result, "reason", None)
            if reason:
                result.setdefault("metric_reasons", {})[name] = str(reason)

        except Exception as exc:
            logger.exception(
                "Metric %s failed for case %s",
                name,
                record["id"],
            )
            result[name] = None
            metric_errors[name] = str(exc)

    if metric_errors:
        result["metric_errors"] = metric_errors

    return result


async def evaluate_case(
    record: dict[str, Any],
    rag: RAG,
    metrics: list[Any],
    top_k: int,
    langfuse: Any | None,
) -> dict[str, Any]:
    """Wrap one evaluation case in a Langfuse trace when enabled."""

    if langfuse is None:
        return await _evaluate_case(record, rag, metrics, top_k)

    case_id = str(record["id"])
    question = str(record["question"])

    try:
        with langfuse.start_as_current_observation(
            as_type="evaluator",
            name="ragas.evaluation_case",
            input={
                "case_id": case_id,
                "question": question,
                "reference": str(record["reference"]),
            },
            metadata={
                "component": "ragas",
                "top_k": top_k,
                "dataset_category": record.get("category"),
                "dataset_difficulty": record.get("difficulty"),
                "ragas_version": package_version("ragas"),
            },
        ) as observation:
            result = await _evaluate_case(
                record=record,
                rag=rag,
                metrics=metrics,
                top_k=top_k,
            )

            observation.update(
                output={
                    "case_id": case_id,
                    "answer": result.get("answer"),
                    "accepted": result.get("accepted"),
                    "latency_seconds": result.get("latency_seconds"),
                    "scores": {
                        name: result.get(name)
                        for name in METRIC_NAMES
                    },
                    "metric_errors": result.get("metric_errors", {}),
                }
            )

            score_langfuse_trace(langfuse, result)
            return result

    except Exception:
        logger.exception(
            "Langfuse-wrapped evaluation failed for case %s.",
            case_id,
        )
        # Do not silently rerun a failed evaluation: generation or
        # retrieval might be expensive and could produce a different answer.
        raise


# ============================================================
# Aggregate results
# ============================================================

def calculate_summary(
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "case_count": len(results),
        "metrics": {},
    }

    for name in METRIC_NAMES:
        values = [
            float(row[name])
            for row in results
            if isinstance(row.get(name), (int, float))
            and math.isfinite(float(row[name]))
        ]

        summary["metrics"][name] = {
            "mean": statistics.fmean(values) if values else None,
            "scored_cases": len(values),
            "total_cases": len(results),
        }

    latencies = [
        float(row["latency_seconds"])
        for row in results
        if isinstance(row.get("latency_seconds"), (int, float))
        and math.isfinite(float(row["latency_seconds"]))
    ]

    summary["latency_seconds"] = {
        "mean": statistics.fmean(latencies) if latencies else None,
        "max": max(latencies) if latencies else None,
        "total_cases": len(latencies),
    }

    return summary


# ============================================================
# MLflow logging
# ============================================================

def log_to_mlflow(
    results: list[dict[str, Any]],
    summary: dict[str, Any],
    output_dir: Path,
    dataset_path: Path,
    top_k: int,
) -> None:
    tracking_uri = env_value("MLFLOW_TRACKING_URI")

    if not tracking_uri:
        logger.info("MLFLOW_TRACKING_URI not set; skipping MLflow.")
        return

    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(
        env_value(
            "MLFLOW_EXPERIMENT_NAME",
            "egyptian-civil-code-rag-evaluation",
        )
    )

    with mlflow.start_run(
        run_name=f"ragas-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}"
    ):
        mlflow.set_tags(
            {
                "evaluation_framework": "RAGAS",
                "langfuse_enabled": str(
                    env_enabled("LANGFUSE_ENABLED")
                ).lower(),
                "qdrant_collection": env_value(
                    "QDRANT_COLLECTION",
                    "test_qwen_embeddings",
                ),
            }
        )

        mlflow.log_params(
            {
                "ragas_version": package_version("ragas"),
                "langfuse_sdk_version": package_version("langfuse"),
                "dataset": str(dataset_path),
                "top_k": top_k,
                "judge_model": env_value(
                    "CHATBOT_MODEL",
                    "Qwen/Qwen2.5-0.5B-Instruct",
                ),
                "embedding_model": env_value(
                    "EMBEDDING_MODEL",
                    "Qwen/Qwen3-Embedding-0.6B",
                ),
                "qdrant_collection": env_value(
                    "QDRANT_COLLECTION",
                    "test_qwen_embeddings",
                ),
                "case_count": len(results),
            }
        )

        for name, data in summary["metrics"].items():
            mean = data["mean"]

            if mean is not None:
                mlflow.log_metric(name, float(mean))

            mlflow.log_metric(
                f"{name}_scored_cases",
                float(data["scored_cases"]),
            )

        mean_latency = summary["latency_seconds"]["mean"]
        max_latency = summary["latency_seconds"]["max"]

        if mean_latency is not None:
            mlflow.log_metric(
                "mean_latency_seconds",
                float(mean_latency),
            )

        if max_latency is not None:
            mlflow.log_metric(
                "max_latency_seconds",
                float(max_latency),
            )

        mlflow.log_artifact(
            str(output_dir / "results.json"),
            artifact_path="evaluation",
        )
        mlflow.log_artifact(
            str(output_dir / "summary.json"),
            artifact_path="evaluation",
        )

        logger.info(
            "Logged evaluation metrics and artifacts to MLflow run %s.",
            mlflow.active_run().info.run_id,
        )


# ============================================================
# Main
# ============================================================

async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate the RAG application with RAGAS."
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("evaluation/datasets/civil_code_eval.jsonl"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("evaluation/results"),
    )
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--no-mlflow", action="store_true")
    args = parser.parse_args()

    if args.top_k < 1:
        parser.error("--top-k must be at least 1")

    if args.limit < 0:
        parser.error("--limit cannot be negative")

    records = load_dataset(args.dataset)
    if args.limit > 0:
        records = records[:args.limit]

    if not records:
        raise ValueError("No evaluation cases to run.")

    args.output_dir.mkdir(parents=True, exist_ok=True)

    langfuse = get_langfuse_client()
    clients: list[AsyncOpenAI] = []

    try:
        logger.info("Loading RAG application...")
        rag = build_rag(top_k=args.top_k)

        logger.info("Initializing RAGAS metrics...")
        metrics, clients = build_metrics()

        results: list[dict[str, Any]] = []
        results_path = args.output_dir / "results.json"

        for index, record in enumerate(records, start=1):
            logger.info(
                "Evaluating case %s/%s: %s",
                index,
                len(records),
                record["id"],
            )

            case_result = await evaluate_case(
                record=record,
                rag=rag,
                metrics=metrics,
                top_k=args.top_k,
                langfuse=langfuse,
            )
            results.append(case_result)

            # Save incrementally so partial results survive interruptions.
            results_path.write_text(
                json.dumps(
                    results,
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                ),
                encoding="utf-8",
            )

        summary = calculate_summary(results)
        summary["dataset"] = str(args.dataset)
        summary["top_k"] = args.top_k
        summary["created_at"] = datetime.now(timezone.utc).isoformat()
        summary["versions"] = {
            "ragas": package_version("ragas"),
            "langfuse": package_version("langfuse"),
            "mlflow": package_version("mlflow"),
        }

        summary_path = args.output_dir / "summary.json"
        summary_path.write_text(
            json.dumps(
                summary,
                ensure_ascii=False,
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )

        if not args.no_mlflow:
            log_to_mlflow(
                results=results,
                summary=summary,
                output_dir=args.output_dir,
                dataset_path=args.dataset,
                top_k=args.top_k,
            )

        print(json.dumps(summary, ensure_ascii=False, indent=2))

    finally:
        for client in clients:
            try:
                await client.close()
            except Exception:
                logger.exception("Failed to close an evaluation API client.")

        flush_langfuse(langfuse)


if __name__ == "__main__":
    asyncio.run(main())
