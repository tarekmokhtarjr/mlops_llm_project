import re
import unicodedata
from typing import Any, Dict, List

from rank_bm25 import BM25Okapi


# ============================================================
# Arabic normalization
# ============================================================

ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
WESTERN_DIGITS = "0123456789"

ARABIC_TO_WESTERN = str.maketrans(
    ARABIC_DIGITS,
    WESTERN_DIGITS,
)


ARABIC_STOP_WORDS = {
    "ما",
    "ماذا",
    "هي",
    "هو",
    "من",
    "في",
    "عن",
    "على",
    "إلى",
    "الى",
    "هل",
    "و",
    "أو",
    "او",
    "التي",
    "الذي",
    "الذين",
    "هذه",
    "هذا",
}


def normalize_digits(text: str) -> str:
    return text.translate(ARABIC_TO_WESTERN)


def normalize_arabic_text(text: str) -> str:
    """
    Conservative Arabic normalization.

    This intentionally does not perform stemming.
    """

    if not text:
        return ""

    text = unicodedata.normalize(
        "NFC",
        text,
    )

    text = normalize_digits(text)

    # Normalize Arabic letter variants.
    text = text.replace("أ", "ا")
    text = text.replace("إ", "ا")
    text = text.replace("آ", "ا")
    text = text.replace("ى", "ي")

    # Remove tashkeel.
    text = re.sub(
        r"[\u0610-\u061A\u064B-\u065F\u0670]",
        "",
        text,
    )

    # Remove tatweel.
    text = text.replace("ـ", "")

    # Remove punctuation.
    text = re.sub(
        r"[^\w\s]",
        " ",
        text,
        flags=re.UNICODE,
    )

    # Normalize whitespace.
    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def tokenize_arabic(text: str) -> List[str]:
    """
    Tokenize Arabic text for BM25.
    """

    normalized = normalize_arabic_text(text)

    if not normalized:
        return []

    tokens = normalized.split()

    return [
        token
        for token in tokens
        if token not in ARABIC_STOP_WORDS
    ]


# ============================================================
# Result wrapper
# ============================================================

class RetrievalResult:
    """
    Compatibility wrapper for retrieved documents.

    Exposes:

        result.payload
        result.score
        result.id
    """

    def __init__(
        self,
        document: Any,
        score: float,
    ) -> None:
        self.document = document
        self.score = score

    @property
    def payload(self):
        return self.document.payload or {}

    @property
    def id(self):
        return self.document.id


# ============================================================
# BM25 lexical search
# ============================================================

def lexical_search(
    query: str,
    documents: list,
    limit: int = 20,
) -> list:
    """
    Perform Arabic BM25 search over the complete document set.

    We include both legal metadata and document content because
    legal hierarchy is highly informative for retrieval.
    """

    if not documents:
        return []

    tokenized_query = tokenize_arabic(query)

    if not tokenized_query:
        return []

    corpus = []

    for document in documents:
        payload = document.payload or {}

        law_number = str(
            payload.get("law_number", "")
        )

        title = str(
            payload.get("title", "")
        )

        content = str(
            payload.get("content", "")
        )

        # The current dataset stores the legal hierarchy in
        # "title". Keep these fields separate here so the
        # searchable representation is explicit and easy to
        # extend if the payload changes later.
        searchable_text = " ".join(
            [
                law_number,
                title,
                content,
            ]
        )

        corpus.append(
            tokenize_arabic(
                searchable_text
            )
        )

    bm25 = BM25Okapi(corpus)

    scores = bm25.get_scores(
        tokenized_query
    )

    ranked_indexes = sorted(
        range(len(documents)),
        key=lambda index: scores[index],
        reverse=True,
    )

    results = []

    for index in ranked_indexes[:limit]:
        score = float(
            scores[index]
        )

        if score <= 0:
            continue

        results.append(
            RetrievalResult(
                document=documents[index],
                score=score,
            )
        )

    return results


# ============================================================
# Reciprocal Rank Fusion
# ============================================================

def reciprocal_rank_fusion(
    semantic_results: List[Dict[str, Any]],
    lexical_results: List[Dict[str, Any]],
    limit: int = 10,
    k: int = 60,
) -> List[RetrievalResult]:
    """
    Combine semantic and lexical rankings using RRF.

    RRF intentionally combines ranks rather than raw scores
    because cosine similarity and BM25 scores have different
    scales.
    """

    fused = {}

    # --------------------------------------------------------
    # Semantic results
    # --------------------------------------------------------

    for result in semantic_results:
        document = result["document"]
        document_id = str(document.id)

        if document_id not in fused:
            fused[document_id] = {
                "document": document,
                "rrf_score": 0.0,
                "semantic_rank": None,
                "lexical_rank": None,
                "semantic_score": None,
                "lexical_score": None,
            }

        rank = result["rank"]

        fused[document_id]["rrf_score"] += (
            1.0 / (k + rank)
        )

        fused[document_id]["semantic_rank"] = rank
        fused[document_id]["semantic_score"] = (
            result.get("score")
        )

    # --------------------------------------------------------
    # Lexical / BM25 results
    # --------------------------------------------------------

    for result in lexical_results:
        document = result["document"]
        document_id = str(document.id)

        if document_id not in fused:
            fused[document_id] = {
                "document": document,
                "rrf_score": 0.0,
                "semantic_rank": None,
                "lexical_rank": None,
                "semantic_score": None,
                "lexical_score": None,
            }

        rank = result["rank"]

        fused[document_id]["rrf_score"] += (
            1.0 / (k + rank)
        )

        fused[document_id]["lexical_rank"] = rank
        fused[document_id]["lexical_score"] = (
            result.get("score")
        )

    # --------------------------------------------------------
    # Sort by fused RRF score
    # --------------------------------------------------------

    ranked = sorted(
        fused.values(),
        key=lambda item: item["rrf_score"],
        reverse=True,
    )

    return [
        RetrievalResult(
            document=item["document"],
            score=item["rrf_score"],
        )
        for item in ranked[:limit]
    ]


# ============================================================
# Hybrid search
# ============================================================

def hybrid_search(
    query: str,
    semantic_results: List[Any],
    lexical_results: List[RetrievalResult],
    limit: int = 10,
) -> List[RetrievalResult]:
    """
    Combine semantic and BM25 retrieval using RRF.
    """

    semantic_ranked = []

    for rank, document in enumerate(
        semantic_results,
        start=1,
    ):
        semantic_ranked.append(
            {
                "document": document,
                "score": getattr(
                    document,
                    "score",
                    0.0,
                ),
                "rank": rank,
            }
        )

    lexical_ranked = []

    for rank, result in enumerate(
        lexical_results,
        start=1,
    ):
        lexical_ranked.append(
            {
                "document": result.document,
                "score": result.score,
                "rank": rank,
            }
        )

    return reciprocal_rank_fusion(
        semantic_results=semantic_ranked,
        lexical_results=lexical_ranked,
        limit=limit,
    )
