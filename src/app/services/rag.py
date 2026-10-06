import re
from dataclasses import dataclass
from typing import Any, List, Optional

from ..clients.vector_db_client import VectorDBClientWrapper
from ..models.embedding import EmbeddingModel
from .retrieval import hybrid_search, lexical_search
from ..models.guard import GuardModel, GuardResult


ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
WESTERN_DIGITS = "0123456789"

ARABIC_TO_WESTERN = str.maketrans(
    ARABIC_DIGITS,
    WESTERN_DIGITS,
)

WESTERN_TO_ARABIC = str.maketrans(
    WESTERN_DIGITS,
    ARABIC_DIGITS,
)


def normalize_digits(text: str) -> str:
    return text.translate(ARABIC_TO_WESTERN)


def extract_article_number(query: str) -> Optional[int]:
    normalized_query = normalize_digits(query)

    patterns = [
        r"المادة\s*(\d+)",
        r"مادة\s*(\d+)",
        r"article\s*#?\s*(\d+)",
    ]
    for pattern in patterns:
        match = re.search(
            pattern,
            normalized_query,
            flags=re.IGNORECASE,
        )
        if match:
            return int(match.group(1))
    return None


def article_number_to_law_number(article_number: int) -> str:
    arabic_number = str(article_number).translate(
        WESTERN_TO_ARABIC
    )
    return f"مادة {arabic_number}"


@dataclass
class RAGRetrievalResult:
    results: List[Any]
    search_type: str
    article_number: Optional[int] = None
    accepted: bool = True
    refusal_reason: Optional[str] = None
    input_guard: Optional[GuardResult] = None
    context_guard: Optional[GuardResult] = None


class RAG:

    def __init__(
        self,
        embedding_model: EmbeddingModel,
        vector_db: VectorDBClientWrapper,
        guard_model: GuardModel,
        retrieval_limit: int = 5,
    ):
        self.embedding_model = embedding_model
        self.vector_db = vector_db
        self.guard_model = guard_model
        self.retrieval_limit = retrieval_limit

    def _build_context(self, results: List[Any]) -> str:
        context_parts = []
        for index, result in enumerate(results, start=1):
            payload = result.payload or {}
            law_number = payload.get("law_number")
            title = payload.get("title")
            content = payload.get("content")
            context_parts.append(
                f"[Document {index}]\n"
                f"Article: {law_number}\n"
                f"Location: {title}\n\n"
                f"{content}"
            )
        return "\n\n".join(context_parts)

    def retrieve_legal_documents(
        self,
        query: str,
        limit: Optional[int] = None,
    ):
        if not query or not query.strip():
            return RAGRetrievalResult(
                results=[],
                search_type="empty",
            )

        # ---------------------------------------------------------
        # 1. Input guard
        # ---------------------------------------------------------

        input_guard = self.guard_model.check_input(query)

        if not input_guard.accepted:
            return RAGRetrievalResult(
                results=[],
                search_type="guard_rejected_input",
            )

        # ---------------------------------------------------------
        # 2. Retrieval
        # ---------------------------------------------------------

        limit = limit or self.retrieval_limit

        article_number = extract_article_number(query)

        if article_number is not None:
            law_number = article_number_to_law_number(
                article_number
            )

            results = self.vector_db.search_article(
                law_number=law_number
            )

            search_type = "exact_article"

        else:
            query_embedding = self.embedding_model.embed(query)

            semantic_limit = max(limit * 4, 20)

            semantic_results = self.vector_db.search(
                query_vector=query_embedding,
                limit=semantic_limit,
            )

            documents = self.vector_db.get_all_documents()

            lexical_results = lexical_search(
                query=query,
                documents=documents,
                limit=semantic_limit,
            )

            results = hybrid_search(
                query=query,
                semantic_results=semantic_results,
                lexical_results=lexical_results,
                limit=limit,
            )

            search_type = "hybrid"

        # ---------------------------------------------------------
        # 3. No results
        # ---------------------------------------------------------

        if not results:
            return RAGRetrievalResult(
                results=[],
                search_type=search_type,
                article_number=article_number,
            )

        # ---------------------------------------------------------
        # 4. Build context
        # ---------------------------------------------------------

        context = self._build_context(results)

        # ---------------------------------------------------------
        # 5. Context guard
        # ---------------------------------------------------------

        context_guard = self.guard_model.check_context(
            query=query,
            context=context,
        )

        if not context_guard.accepted:
            return RAGRetrievalResult(
                results=[],
                search_type="guard_rejected_context",
                article_number=article_number,
            )

        # ---------------------------------------------------------
        # 6. Return retrieved documents
        # ---------------------------------------------------------

        return RAGRetrievalResult(
            results=results,
            search_type=search_type,
            article_number=article_number,
        )

    def retrieve_legal_documents(
        self,
        query: str,
        limit: Optional[int] = None,
    ) -> RAGRetrievalResult:
        if not query or not query.strip():
            return RAGRetrievalResult(
                results=[],
                search_type="empty",
            )
        limit = limit or self.retrieval_limit
        article_number = extract_article_number(query)
        # Exact article lookup
        if article_number is not None:
            law_number = article_number_to_law_number(
                article_number
            )
            results = self.vector_db.search_article(
                law_number=law_number
            )
            return RAGRetrievalResult(
                results=results,
                search_type="exact_article",
                article_number=article_number,
            )
        # Semantic retrieval
        query_embedding = self.embedding_model.embed(query)
        semantic_limit = max(limit * 4, 20)
        semantic_results = self.vector_db.search(
            query_vector=query_embedding,
            limit=semantic_limit,
        )
        # Lexical retrieval
        documents = self.vector_db.get_all_documents()
        lexical_results = lexical_search(
            query=query,
            documents=documents,
            limit=semantic_limit,
        )
        # Hybrid retrieval using Reciprocal Rank Fusion
        results = hybrid_search(
            query=query,
            semantic_results=semantic_results,
            lexical_results=lexical_results,
            limit=limit,
        )
        return RAGRetrievalResult(
            results=results,
            search_type="hybrid",
        )


def serialize_result(result: Any) -> dict:
    payload = result.payload or {}
    return {
        "law_number": payload.get("law_number"),
        "title": payload.get("title"),
        "content": payload.get("content"),
        "score": getattr(result, "score", None),
    }
