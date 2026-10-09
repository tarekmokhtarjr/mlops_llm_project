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
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

METRIC_NAMES = (
    "faithfulness",
    "answer_relevancy",
    "answer_correctness",
    "context_precision",
    "context_recall",
    "hit_rate",
    "precision_at_k",
    "recall_at_k",
    "mrr",
)


# ============================================================
# Dataset loading
# ============================================================

def load_dataset(path: Path) -> list[dict[str, Any]]:
    """Load a JSON array, a {'data': [...]} object, or JSONL."""

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

    required = {
        "id",
        "question",
        "reference",
        "relevant_document_ids",
    }

    seen_ids: set[str] = set()

    for index, record in enumerate(records, start=1):
        missing = required - record.keys()

        if missing:
            raise ValueError(
                f"Dataset record {index} is missing: "
                f"{sorted(missing)}"
            )

        record_id = str(record["id"])

        if record_id in seen_ids:
            raise ValueError(
                f"Duplicate dataset ID: {record_id}"
            )

        seen_ids.add(record_id)

        if not str(record["question"]).strip():
            raise ValueError(
                f"Empty question in record {record_id}"
            )

        if not isinstance(
            record["relevant_document_ids"], list
        ):
            raise ValueError(
                "relevant_document_ids must be a list "
                f"in record {record_id}"
            )

    return records


# ============================================================
# Environment and RAG initialization
# ============================================================

def env_value(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


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

    # Accept either a hostname or a URL already containing a port.
    if re.search(r":\d+$", server):
        return f"{server}/v1"

    return f"{server}:{port}/v1"


def build_metrics() -> tuple[list[Any], list[AsyncOpenAI]]:
    """Create RAGAS 0.4.3 metrics using the existing vLLM services."""

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

    embedding_key = env_value(
        "EMBEDDING_MODEL_API_KEY",
        "dumb",
    )

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
# Document helpers
# ============================================================

def get_payload(document: Any) -> dict[str, Any]:
    payload = getattr(document, "payload", None)
    return payload if isinstance(payload, dict) else {}


def document_text(document: Any) -> str:
    """Format the retrieved Qdrant payload as evaluation context."""

    payload = get_payload(document)

    article = str(payload.get("law_number", ""))
    title = str(payload.get("title", ""))
    content = str(payload.get("content", ""))

    parts = [
        f"Article: {article}",
        f"Legal hierarchy: {title}",
        f"Text: {content}",
    ]

    return "\n".join(parts).strip()


def document_identifiers(document: Any) -> set[str]:
    """Expose both Qdrant point ID and article-number identifiers."""

    identifiers: set[str] = set()

    point_id = getattr(document, "id", None)

    if point_id is not None:
        identifiers.add(str(point_id).strip())

    payload = get_payload(document)
    law_number = str(payload.get("law_number", "")).strip()

    if law_number:
        identifiers.add(law_number)

        # Support datasets that identify documents by article number,
        # e.g. "89" versus a payload containing "مادة ٨٩".
        digits = re.sub(
            r"[٠-٩]",
            lambda match: str("٠١٢٣٤٥٦٧٨٩".index(match.group())),
            law_number,
        )
        article_match = re.search(r"\d+", digits)

        if article_match:
            identifiers.add(article_match.group())

    return identifiers


def normalize_reference_id(value: Any) -> str:
    value = str(value).strip()

    if re.fullmatch(r"\d+", value):
        return value

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
    Calculate ID-based metrics.

    These metrics are meaningful only if relevant_document_ids
    correspond to actual Qdrant point IDs or article identifiers.
    """

    expected = {
        normalize_reference_id(value)
        for value in relevant_ids
    }

    if not expected:
        # No gold IDs means retrieval precision/recall cannot
        # be evaluated against an annotated relevant set.
        return {
            "hit_rate": None,
            "precision_at_k": None,
            "recall_at_k": None,
            "mrr": None,
        }

    ranked_ids: list[set[str]] = [
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
            for rank, is_relevant in enumerate(
                relevant_flags,
                start=1,
            )
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
# Generate an answer from the SAME retrieval result
# ============================================================

def generate_from_retrieval(
    rag: RAG,
    question: str,
    retrieval: Any,
) -> str:
    """
    Avoid calling rag.answer(question) here because it would
    retrieve documents a second time.
    """

    if not retrieval.accepted:
        return (
            retrieval.refusal_reason
            or "The request was rejected by a guard."
        )

    if not retrieval.results:
        return "لم يتم العثور على سياق قانوني مناسب للإجابة عن السؤال."

    context = rag._build_context(retrieval.results)

    prompt = rag._build_prompt(
        query=question,
        context=context,
    )

    return rag.chat_model.invoke(prompt).strip()


# ============================================================
# RAGAS 0.4.3 scoring
# ============================================================

def score_value(result: Any) -> float | None:
    value = getattr(result, "value", None)

    if value is None:
        return None

    value = float(value)

    if not math.isfinite(value):
        return None

    return value


async def evaluate_case(
    record: dict[str, Any],
    rag: RAG,
    metrics: list[Any],
    top_k: int,
) -> dict[str, Any]:
    question = str(record["question"])
    reference = str(record["reference"])

    started = time.perf_counter()

    # Retrieve exactly once; generation and evaluation use these results.
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

    elapsed_seconds = time.perf_counter() - started

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
                "law_number": get_payload(document).get(
                    "law_number"
                ),
                "title": get_payload(document).get("title"),
                "content": get_payload(document).get("content"),
                "score": getattr(document, "score", None),
            }
            for document in retrieved_documents
        ],
        "retrieved_contexts": contexts,
        "latency_seconds": round(elapsed_seconds, 4),
    }

    result.update(
        calculate_retrieval_metrics(
            retrieved_documents=retrieved_documents,
            relevant_ids=record["relevant_document_ids"],
        )
    )

    # RAGAS metrics that require an answer/context/reference cannot
    # be scored meaningfully if the system returned no context.
    if not contexts or not answer.strip():
        for name in (
            "faithfulness",
            "answer_relevancy",
            "answer_correctness",
            "context_precision",
            "context_recall",
        ):
            result[name] = None

        result["metric_errors"] = (
            "No retrieved contexts or no generated answer."
        )
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

    result["metric_errors"] = {}

    for metric in metrics:
        name = metric.name
        try:
            metric_result = await metric.ascore(
                **metric_inputs[name]
            )
            result[name] = score_value(metric_result)

            reason = getattr(metric_result, "reason", None)
            if reason:
                result.setdefault("metric_reasons", {})[name] = str(
                    reason
                )

        except Exception as exc:
            logger.exception(
                "Metric %s failed for case %s",
                name,
                record["id"],
            )
            result[name] = None
            result["metric_errors"][name] = str(exc)

    if not result["metric_errors"]:
        result.pop("metric_errors")

    return result


# ============================================================
# Aggregate results and MLflow
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

    return summary


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
        mlflow.log_params(
            {
                "ragas_version": "0.4.3",
                "dataset": str(dataset_path),
                "top_k": top_k,
                "judge_model": env_value("CHATBOT_MODEL"),
                "embedding_model": env_value("EMBEDDING_MODEL"),
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

        mlflow.log_artifact(
            str(output_dir / "results.json"),
            artifact_path="evaluation",
        )
        mlflow.log_artifact(
            str(output_dir / "summary.json"),
            artifact_path="evaluation",
        )


# ============================================================
# Main
# ============================================================

async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate the RAG application with RAGAS 0.4.3."
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

    records = load_dataset(args.dataset)

    if args.limit > 0:
        records = records[: args.limit]

    if not records:
        raise ValueError("No evaluation cases to run.")

    args.output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Loading RAG application...")
    rag = build_rag(top_k=args.top_k)

    logger.info("Initializing RAGAS 0.4.3 metrics...")
    metrics, clients = build_metrics()

    results: list[dict[str, Any]] = []

    try:
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
            )

            results.append(case_result)

            # Save incrementally so partial results survive a later failure.
            (args.output_dir / "results.json").write_text(
                json.dumps(
                    results,
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                ),
                encoding="utf-8",
            )

    finally:
        for client in clients:
            await client.close()

    summary = calculate_summary(results)
    summary["dataset"] = str(args.dataset)
    summary["top_k"] = args.top_k
    summary["created_at"] = datetime.now(
        timezone.utc
    ).isoformat()

    (args.output_dir / "summary.json").write_text(
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


if __name__ == "__main__":
    asyncio.run(main())
