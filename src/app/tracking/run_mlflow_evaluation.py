from __future__ import annotations

import argparse
import json
import os
import statistics
import time
from pathlib import Path
from typing import Any

import mlflow
from dotenv import load_dotenv

from app.clients.vector_db_client import VectorDBClientWrapper
from app.tracking.mlflow_metrics import (
    aggregate_retrieval_metrics,
    calculate_retrieval_metrics,
    average,
    safe_rate,
)
from app.models.embedding import EmbeddingModel
from app.models.guard import GuardModel
from app.services.rag import RAG, serialize_result


load_dotenv()


def load_dataset(
    path: str,
) -> list[dict[str, Any]]:

    dataset_path = Path(path)

    if not dataset_path.exists():
        raise FileNotFoundError(
            f"Evaluation dataset not found: {path}"
        )

    records = []

    with dataset_path.open(
        "r",
        encoding="utf-8",
    ) as file:

        for line_number, line in enumerate(
            file,
            start=1,
        ):
            line = line.strip()

            if not line:
                continue

            try:
                records.append(
                    json.loads(line)
                )
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON on line "
                    f"{line_number}"
                ) from exc

    return records


def document_identifier(
    result: Any,
) -> str:

    payload = result.payload or {}

    # Prefer the actual Qdrant point ID.
    if getattr(result, "id", None) is not None:
        return str(result.id)

    # Fallback to legal article number.
    law_number = payload.get(
        "law_number"
    )

    if law_number:
        return str(law_number)

    return str(
        payload.get(
            "content",
            "",
        )
    )


def extract_relevant_ids(
    record: dict[str, Any],
) -> set[str]:

    values = record.get(
        "relevant_document_ids",
        [],
    )

    return {
        str(value)
        for value in values
    }


def log_parameters() -> None:

    parameter_names = [
        "CHATBOT_MODEL",
        "EMBEDDING_MODEL",
        "GUARD_MODEL",
        "QDRANT_COLLECTION",
    ]

    for name in parameter_names:
        value = os.getenv(name)

        if value is not None:
            mlflow.log_param(
                name.lower(),
                value,
            )

    mlflow.log_param(
        "retrieval_top_k",
        5,
    )

    mlflow.log_param(
        "semantic_top_k",
        20,
    )

    mlflow.log_param(
        "retrieval_method",
        "hybrid_rrf",
    )

    mlflow.log_param(
        "embedding_server",
        os.getenv(
            "EMBEDDING_MODEL_SERVER"
        ),
    )

    mlflow.log_param(
        "guard_server",
        os.getenv(
            "GUARD_MODEL_SERVER"
        ),
    )


def evaluate(
    dataset_path: str,
) -> None:

    tracking_uri = os.getenv(
        "MLFLOW_TRACKING_URI",
        "http://localhost:5000",
    )

    experiment_name = os.getenv(
        "MLFLOW_EXPERIMENT_NAME",
        "egyptian-civil-code-rag",
    )

    mlflow.set_tracking_uri(
        tracking_uri
    )

    mlflow.set_experiment(
        experiment_name
    )

    dataset = load_dataset(
        dataset_path
    )

    embedding_model = EmbeddingModel()

    guard_model = GuardModel()

    vector_db = VectorDBClientWrapper(
        url=(
            f"http://"
            f"{os.getenv('QDRANT_HOST')}:"
            f"{os.getenv('QDRANT_PORT')}"
        ),
        collection_name=os.getenv(
            "QDRANT_COLLECTION"
        ),
    )

    rag = RAG(
        embedding_model=embedding_model,
        vector_db=vector_db,
        guard_model=guard_model,
        retrieval_limit=5,
    )

    with mlflow.start_run() as run:

        log_parameters()

        retrieval_metrics = []

        input_guard_results = []
        context_guard_results = []

        total_latencies = []
        retrieval_latencies = []
        guard_latencies = []

        detailed_results = []

        for record in dataset:

            query = record["question"]

            relevant_ids = (
                extract_relevant_ids(
                    record
                )
            )

            started_at = time.perf_counter()

            response = (
                rag.retrieve_legal_documents(
                    query
                )
            )

            total_latency = (
                time.perf_counter()
                - started_at
            ) * 1000

            total_latencies.append(
                total_latency
            )

            input_guard = (
                response.input_guard
            )

            context_guard = (
                response.context_guard
            )

            if input_guard is not None:
                input_guard_results.append(
                    input_guard.accepted
                )

            if context_guard is not None:
                context_guard_results.append(
                    context_guard.accepted
                )

            serialized = [
                serialize_result(result)
                for result in response.results
            ]

            ranked_ids = [
                document_identifier(
                    result
                )
                for result in response.results
            ]

            if relevant_ids:

                metric = (
                    calculate_retrieval_metrics(
                        ranked_document_ids=ranked_ids,
                        relevant_document_ids=relevant_ids,
                        k=5,
                    )
                )

                retrieval_metrics.append(
                    metric
                )

            detailed_results.append(
                {
                    "question": query,
                    "search_type": (
                        response.search_type
                    ),
                    "accepted": (
                        response.accepted
                    ),
                    "article_number": (
                        response.article_number
                    ),
                    "latency_ms": (
                        total_latency
                    ),
                    "relevant_document_ids": (
                        list(relevant_ids)
                    ),
                    "retrieved_document_ids": (
                        ranked_ids
                    ),
                    "results": serialized,
                }
            )

        # ----------------------------------------------------
        # Retrieval metrics
        # ----------------------------------------------------

        aggregated = (
            aggregate_retrieval_metrics(
                retrieval_metrics
            )
        )

        if aggregated:
            mlflow.log_metrics(
                aggregated
            )

        # ----------------------------------------------------
        # Guard metrics
        # ----------------------------------------------------

        if input_guard_results:

            mlflow.log_metric(
                "input_guard_safe_rate",
                safe_rate(
                    input_guard_results
                ),
            )

            mlflow.log_metric(
                "input_guard_rejection_rate",
                1.0
                - safe_rate(
                    input_guard_results
                ),
            )

        if context_guard_results:

            mlflow.log_metric(
                "context_guard_safe_rate",
                safe_rate(
                    context_guard_results
                ),
            )

            mlflow.log_metric(
                "context_guard_rejection_rate",
                1.0
                - safe_rate(
                    context_guard_results
                ),
            )

        # ----------------------------------------------------
        # Latency metrics
        # ----------------------------------------------------

        if total_latencies:

            mlflow.log_metric(
                "total_latency_ms_mean",
                average(
                    total_latencies
                ),
            )

            mlflow.log_metric(
                "total_latency_ms_p50",
                statistics.median(
                    total_latencies
                ),
            )

            if len(total_latencies) >= 2:
                mlflow.log_metric(
                    "total_latency_ms_p95",
                    sorted(
                        total_latencies
                    )[
                        max(
                            0,
                            int(
                                len(total_latencies)
                                * 0.95
                            ) - 1,
                        )
                    ],
                )

        # ----------------------------------------------------
        # Dataset metrics
        # ----------------------------------------------------

        mlflow.log_metric(
            "evaluation_questions",
            len(dataset),
        )

        mlflow.log_metric(
            "questions_with_retrieval_ground_truth",
            len(retrieval_metrics),
        )

        # ----------------------------------------------------
        # Artifacts
        # ----------------------------------------------------

        artifact_path = Path(
            "/tmp/mlflow_evaluation_results.json"
        )

        artifact_path.write_text(
            json.dumps(
                detailed_results,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        mlflow.log_artifact(
            str(artifact_path),
            artifact_path="evaluation",
        )

        print(
            f"MLflow run completed: {run.info.run_id}"
        )


def main():

    parser = argparse.ArgumentParser(
        description=(
            "Evaluate the RAG system and "
            "log metrics to MLflow."
        )
    )

    parser.add_argument(
        "--dataset",
        required=True,
        help="Path to JSONL evaluation dataset.",
    )

    args = parser.parse_args()

    evaluate(
        dataset_path=args.dataset
    )


if __name__ == "__main__":
    main()