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


def normalize_digits(
    text: str,
) -> str:

    return text.translate(
        ARABIC_TO_WESTERN
    )


def normalize_arabic_text(
    text: str,
) -> str:
    """
    Conservative Arabic normalization.

    This is intentionally NOT an Arabic stemmer.
    """

    if not text:
        return ""

    text = unicodedata.normalize(
        "NFC",
        text,
    )

    # Arabic-Indic digits -> Western digits
    text = normalize_digits(
        text
    )

    # Normalize Arabic letter variants
    text = text.replace(
        "أ",
        "ا",
    )

    text = text.replace(
        "إ",
        "ا",
    )

    text = text.replace(
        "آ",
        "ا",
    )

    text = text.replace(
        "ى",
        "ي",
    )

    # Remove tashkeel
    text = re.sub(
        r"[\u0610-\u061A\u064B-\u065F\u0670]",
        "",
        text,
    )

    # Remove tatweel
    text = text.replace(
        "ـ",
        "",
    )

    # Remove punctuation
    text = re.sub(
        r"[^\w\s]",
        " ",
        text,
        flags=re.UNICODE,
    )

    # Normalize whitespace
    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def tokenize_arabic(
    text: str,
) -> List[str]:
    """
    Tokenize Arabic text for BM25.
    """

    normalized = normalize_arabic_text(
        text
    )

    if not normalized:
        return []

    tokens = normalized.split()

    return [
        token
        for token in tokens
        if token not in ARABIC_STOP_WORDS
    ]


# ============================================================
# BM25 lexical search
# ============================================================

def lexical_search(
    query: str,
    documents: list,
    limit: int = 20,
) -> list:
    if not documents:
        return []

    tokenized_query = tokenize_arabic(query)

    if not tokenized_query:
        return []

    corpus = []

    for document in documents:
        payload = document.payload or {}

        law_number = str(payload.get("law_number", ""))
        title = str(payload.get("title", ""))
        content = str(payload.get("content", ""))

        searchable_text = " ".join(
            [
                law_number,
                title,
                content,
            ]
        )

        corpus.append(tokenize_arabic(searchable_text))

    bm25 = BM25Okapi(corpus)

    scores = bm25.get_scores(tokenized_query)

    ranked_indexes = sorted(
        range(len(documents)),
        key=lambda index: scores[index],
        reverse=True,
    )

    results = []

    for index in ranked_indexes[:limit]:
        score = float(scores[index])

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
) -> List[Any]:
    """
    Combine semantic and lexical rankings using RRF.

    RRF:

        score = 1 / (k + rank)

    We deliberately DO NOT combine the raw cosine
    similarity and BM25 scores because they have
    different scales.
    """

    fused = {}

    # --------------------------------------------------------
    # Semantic results
    # --------------------------------------------------------

    for result in semantic_results:

        document = result["document"]

        document_id = str(
            document.id
        )

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

        fused[
            document_id
        ][
            "rrf_score"
        ] += (
            1.0
            / (
                k + rank
            )
        )

        fused[
            document_id
        ][
            "semantic_rank"
        ] = rank

        fused[
            document_id
        ][
            "semantic_score"
        ] = result.get(
            "score"
        )

    # --------------------------------------------------------
    # Lexical / BM25 results
    # --------------------------------------------------------

    for result in lexical_results:

        document = result["document"]

        document_id = str(
            document.id
        )

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

        fused[
            document_id
        ][
            "rrf_score"
        ] += (
            1.0
            / (
                k + rank
            )
        )

        fused[
            document_id
        ][
            "lexical_rank"
        ] = rank

        fused[
            document_id
        ][
            "lexical_score"
        ] = result.get(
            "score"
        )

    # --------------------------------------------------------
    # Sort by RRF score
    # --------------------------------------------------------

    ranked = sorted(
        fused.values(),
        key=lambda item: item[
            "rrf_score"
        ],
        reverse=True,
    )

    # --------------------------------------------------------
    # Return Qdrant-like documents
    #
    # Your Streamlit code expects:
    #
    # result.payload
    # result.score
    #
    # Therefore we attach the RRF score directly
    # to the Qdrant result object.
    # --------------------------------------------------------

    final_results = []

    for item in ranked[:limit]:

        document = item[
            "document"
        ]

        # Preserve the original document object.
        #
        # Streamlit's serialize_result() expects
        # document.payload and document.score.
        #
        # Qdrant ScoredPoint normally allows score
        # to be read, but we don't want to mutate
        # the object in an unsafe way.
        #
        # Instead, return a small wrapper.

        final_results.append(
            RetrievalResult(
                document=document,
                score=item[
                    "rrf_score"
                ],
            )
        )

    return final_results


# ============================================================
# Result wrapper
# ============================================================

class RetrievalResult:
    """
    Small compatibility wrapper.

    It exposes the same attributes that the current
    Streamlit code expects:

        result.payload
        result.score
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

        return (
            self.document.payload
            or {}
        )

    @property
    def id(self):

        return self.document.id


# ============================================================
# Hybrid search
# ============================================================

def hybrid_search(
    query: str,
    semantic_results: List[Any],
    lexical_results: List[RetrievalResult],
    limit: int = 5,
) -> List[RetrievalResult]:
    semantic_ranked = []

    for rank, document in enumerate(semantic_results, start=1):
        semantic_ranked.append(
            {
                "document": document,
                "score": getattr(document, "score", 0.0),
                "rank": rank,
            }
        )

    lexical_ranked = []

    for rank, result in enumerate(lexical_results, start=1):
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
