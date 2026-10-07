from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass
class RetrievalMetrics:
    hit_rate_at_1: float
    hit_rate_at_3: float
    hit_rate_at_5: float
    recall_at_5: float
    precision_at_5: float
    mrr: float
    ndcg_at_5: float


def _dcg(relevances: list[int]) -> float:
    score = 0.0

    for rank, relevance in enumerate(
        relevances,
        start=1,
    ):
        if relevance:
            score += relevance / __import__(
                "math"
            ).log2(rank + 1)

    return score


def _ndcg(relevances: list[int]) -> float:
    if not relevances:
        return 0.0

    actual = _dcg(relevances)

    ideal = _dcg(
        sorted(
            relevances,
            reverse=True,
        )
    )

    if ideal == 0:
        return 0.0

    return actual / ideal


def calculate_retrieval_metrics(
    ranked_document_ids: list[str],
    relevant_document_ids: set[str],
    k: int = 5,
) -> RetrievalMetrics:

    if not relevant_document_ids:
        return RetrievalMetrics(
            hit_rate_at_1=0.0,
            hit_rate_at_3=0.0,
            hit_rate_at_5=0.0,
            recall_at_5=0.0,
            precision_at_5=0.0,
            mrr=0.0,
            ndcg_at_5=0.0,
        )

    top_1 = ranked_document_ids[:1]
    top_3 = ranked_document_ids[:3]
    top_5 = ranked_document_ids[:k]

    hit_rate_at_1 = float(
        any(
            document_id in relevant_document_ids
            for document_id in top_1
        )
    )

    hit_rate_at_3 = float(
        any(
            document_id in relevant_document_ids
            for document_id in top_3
        )
    )

    hit_rate_at_5 = float(
        any(
            document_id in relevant_document_ids
            for document_id in top_5
        )
    )

    relevant_retrieved = sum(
        document_id in relevant_document_ids
        for document_id in top_5
    )

    recall_at_5 = (
        relevant_retrieved
        / len(relevant_document_ids)
    )

    precision_at_5 = (
        relevant_retrieved
        / len(top_5)
        if top_5
        else 0.0
    )

    reciprocal_rank = 0.0

    for rank, document_id in enumerate(
        ranked_document_ids,
        start=1,
    ):
        if document_id in relevant_document_ids:
            reciprocal_rank = 1.0 / rank
            break

    relevances = [
        int(
            document_id in relevant_document_ids
        )
        for document_id in top_5
    ]

    return RetrievalMetrics(
        hit_rate_at_1=hit_rate_at_1,
        hit_rate_at_3=hit_rate_at_3,
        hit_rate_at_5=hit_rate_at_5,
        recall_at_5=recall_at_5,
        precision_at_5=precision_at_5,
        mrr=reciprocal_rank,
        ndcg_at_5=_ndcg(relevances),
    )


def aggregate_retrieval_metrics(
    metrics: Iterable[RetrievalMetrics],
) -> dict[str, float]:

    metrics = list(metrics)

    if not metrics:
        return {}

    count = len(metrics)

    return {
        "retrieval_hit_rate_at_1": sum(
            metric.hit_rate_at_1
            for metric in metrics
        ) / count,

        "retrieval_hit_rate_at_3": sum(
            metric.hit_rate_at_3
            for metric in metrics
        ) / count,

        "retrieval_hit_rate_at_5": sum(
            metric.hit_rate_at_5
            for metric in metrics
        ) / count,

        "retrieval_recall_at_5": sum(
            metric.recall_at_5
            for metric in metrics
        ) / count,

        "retrieval_precision_at_5": sum(
            metric.precision_at_5
            for metric in metrics
        ) / count,

        "retrieval_mrr": sum(
            metric.mrr
            for metric in metrics
        ) / count,

        "retrieval_ndcg_at_5": sum(
            metric.ndcg_at_5
            for metric in metrics
        ) / count,
    }


def average(
    values: Iterable[float],
) -> float:

    values = list(values)

    if not values:
        return 0.0

    return sum(values) / len(values)


def safe_rate(
    values: Iterable[bool],
) -> float:

    values = list(values)

    if not values:
        return 0.0

    return sum(
        bool(value)
        for value in values
    ) / len(values)