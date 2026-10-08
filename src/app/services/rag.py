import re
from dataclasses import dataclass
from typing import Any, List, Optional

from ..clients.vector_db_client import VectorDBClientWrapper
from ..models.chat import ChatBotLlmModel
from ..models.embedding import EmbeddingModel
from ..models.guard import GuardModel, GuardResult
from .retrieval import hybrid_search, lexical_search


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


def article_number_to_law_number(
    article_number: int,
) -> str:

    arabic_number = str(
        article_number
    ).translate(
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
        chat_model: ChatBotLlmModel,
        retrieval_limit: int = 5,
    ):
        self.embedding_model = embedding_model
        self.vector_db = vector_db
        self.guard_model = guard_model
        self.chat_model = chat_model
        self.retrieval_limit = retrieval_limit

    def _build_context(
        self,
        results: List[Any],
    ) -> str:

        context_parts = []

        for index, result in enumerate(
            results,
            start=1,
        ):
            payload = result.payload or {}

            law_number = payload.get(
                "law_number"
            )

            title = payload.get(
                "title"
            )

            content = payload.get(
                "content"
            )

            context_parts.append(
                f"[Document {index}]\n"
                f"Article: {law_number}\n"
                f"Location: {title}\n\n"
                f"{content}"
            )

        return "\n\n".join(
            context_parts
        )

    def retrieve_legal_documents(
        self,
        query: str,
        limit: Optional[int] = None,
    ) -> RAGRetrievalResult:

        # ---------------------------------------------------------
        # 0. Empty query
        # ---------------------------------------------------------

        if not query or not query.strip():
            return RAGRetrievalResult(
                results=[],
                search_type="empty",
            )

        # ---------------------------------------------------------
        # 1. INPUT GUARD
        # ---------------------------------------------------------

        input_guard = (
            self.guard_model.check_input(
                query
            )
        )

        if not input_guard.accepted:
            return RAGRetrievalResult(
                results=[],
                search_type="guard_rejected_input",
                accepted=False,
                refusal_reason=(
                    "Input rejected by safety guard."
                ),
                input_guard=input_guard,
            )

        # ---------------------------------------------------------
        # 2. RETRIEVAL
        # ---------------------------------------------------------

        limit = (
            limit
            or self.retrieval_limit
        )

        article_number = (
            extract_article_number(
                query
            )
        )

        # ---------------------------------------------------------
        # 2a. Exact article lookup
        # ---------------------------------------------------------

        if article_number is not None:

            law_number = (
                article_number_to_law_number(
                    article_number
                )
            )

            results = (
                self.vector_db.search_article(
                    law_number=law_number
                )
            )

            search_type = "exact_article"

        # ---------------------------------------------------------
        # 2b. Hybrid retrieval
        # ---------------------------------------------------------

        else:

            query_embedding = (
                self.embedding_model.embed(
                    query
                )
            )

            semantic_limit = max(
                limit * 4,
                20,
            )

            semantic_results = (
                self.vector_db.search(
                    query_vector=query_embedding,
                    limit=semantic_limit,
                )
            )

            documents = (
                self.vector_db.get_all_documents()
            )

            lexical_results = (
                lexical_search(
                    query=query,
                    documents=documents,
                    limit=semantic_limit,
                )
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
                accepted=True,
                input_guard=input_guard,
            )

        # ---------------------------------------------------------
        # 4. Build context
        # ---------------------------------------------------------

        context = self._build_context(
            results
        )

        # ---------------------------------------------------------
        # 5. CONTEXT GUARD
        # ---------------------------------------------------------

        context_guard = (
            self.guard_model.check_context(
                query=query,
                context=context,
            )
        )

        if not context_guard.accepted:

            return RAGRetrievalResult(
                results=[],
                search_type="guard_rejected_context",
                article_number=article_number,
                accepted=False,
                refusal_reason=(
                    "Retrieved context rejected "
                    "by safety guard."
                ),
                input_guard=input_guard,
                context_guard=context_guard,
            )

        # ---------------------------------------------------------
        # 6. Successful retrieval
        # ---------------------------------------------------------

        return RAGRetrievalResult(
            results=results,
            search_type=search_type,
            article_number=article_number,
            accepted=True,
            input_guard=input_guard,
            context_guard=context_guard,
        )

    def _build_prompt(
        self,
        query: str,
        context: str,
    ) -> str:

        return f"""
You are a legal information assistant.

Answer the user's question using ONLY the
provided Egyptian Civil Code context.

Do not invent legal provisions or facts.

If the context does not contain enough
information to answer the question, say:

"لا تتوفر معلومات كافية في السياق المسترجع
للإجابة عن هذا السؤال."

When relevant, mention the article number
that supports your answer.

User question:
{query}

Retrieved context:
<context>
{context}
</context>

Answer:
""".strip()

    def answer(
        self,
        query: str,
    ) -> str:

        # ---------------------------------------------------------
        # 1. Retrieve and guard context
        # ---------------------------------------------------------

        retrieval = (
            self.retrieve_legal_documents(
                query
            )
        )

        if not retrieval.accepted:
            return (
                retrieval.refusal_reason
                or "Unable to process the request."
            )

        if not retrieval.results:
            return (
                "لم يتم العثور على سياق قانوني "
                "مناسب للإجابة عن السؤال."
            )

        # ---------------------------------------------------------
        # 2. Build context
        # ---------------------------------------------------------

        context = self._build_context(
            retrieval.results
        )

        # ---------------------------------------------------------
        # 3. Build LLM prompt
        # ---------------------------------------------------------

        prompt = self._build_prompt(
            query=query,
            context=context,
        )

        # ---------------------------------------------------------
        # 4. Generate answer
        # ---------------------------------------------------------

        return self.chat_model.invoke(
            prompt
        )


def serialize_result(
    result: Any,
) -> dict:

    payload = result.payload or {}

    return {
        "law_number": payload.get(
            "law_number"
        ),
        "title": payload.get(
            "title"
        ),
        "content": payload.get(
            "content"
        ),
        "score": getattr(
            result,
            "score",
            None,
        ),
    }