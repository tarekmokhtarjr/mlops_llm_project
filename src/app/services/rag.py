import re
from dataclasses import dataclass
import logging
import os
from typing import Any, List, Optional

from ..clients.vector_db_client import VectorDBClientWrapper
from ..models.chat import ChatBotLlmModel
from ..models.embedding import EmbeddingModel
from ..models.guard import GuardModel, GuardResult
from .retrieval import hybrid_search, lexical_search
from ..tracking.langfuse_tracing import get_langfuse_client

logger = logging.getLogger(__name__)

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
    return text.translate(
        ARABIC_TO_WESTERN
    )


def extract_article_number(
    query: str,
) -> Optional[int]:
    normalized_query = normalize_digits(
        query
    )

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
            return int(
                match.group(1)
            )

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
        retrieval_limit: int = 10,
    ):
        self.embedding_model = embedding_model
        self.vector_db = vector_db
        self.guard_model = guard_model
        self.chat_model = chat_model
        self.retrieval_limit = retrieval_limit

    # ========================================================
    # Context construction
    # ========================================================

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

            law_number = str(
                payload.get(
                    "law_number",
                    "",
                )
            )

            title = str(
                payload.get(
                    "title",
                    "",
                )
            )

            content = str(
                payload.get(
                    "content",
                    "",
                )
            )

            context_parts.append(
                f"[LEGAL_DOCUMENT_{index}]\n"
                f"Article: {law_number}\n"
                f"Legal hierarchy: {title}\n"
                f"Text:\n"
                f"{content}\n"
                f"[END_LEGAL_DOCUMENT_{index}]"
            )

        return "\n\n".join(
            context_parts
        )

    # ========================================================
    # Retrieval
    # ========================================================

    def retrieve_legal_documents(
        self,
        query: str,
        limit: Optional[int] = None,
    ) -> RAGRetrievalResult:

        # ----------------------------------------------------
        # 0. Empty query
        # ----------------------------------------------------

        if not query or not query.strip():
            return RAGRetrievalResult(
                results=[],
                search_type="empty",
            )

        # ----------------------------------------------------
        # 1. Input guard
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # 2. Retrieval configuration
        # ----------------------------------------------------

        limit = (
            limit
            if limit is not None
            else self.retrieval_limit
        )

        article_number = (
            extract_article_number(
                query
            )
        )

        # ----------------------------------------------------
        # 2a. Exact article lookup
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # 2b. Hybrid retrieval
        # ----------------------------------------------------

        else:
            query_embedding = (
                self.embedding_model.embed(
                    query
                )
            )

            # Retrieve a larger candidate set from both
            # retrieval methods before RRF.
            semantic_limit = max(
                limit * 2,
                20,
            )

            semantic_results = (
                self.vector_db.search(
                    query_vector=query_embedding,
                    limit=semantic_limit,
                )
            )

            # BM25 searches the complete collection.
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

        # ----------------------------------------------------
        # 3. No results
        # ----------------------------------------------------

        if not results:
            return RAGRetrievalResult(
                results=[],
                search_type=search_type,
                article_number=article_number,
                accepted=True,
                input_guard=input_guard,
            )

        # ----------------------------------------------------
        # 4. Build context
        # ----------------------------------------------------

        context = self._build_context(
            results
        )

        # ----------------------------------------------------
        # 5. Context guard
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # 6. Successful retrieval
        # ----------------------------------------------------

        return RAGRetrievalResult(
            results=results,
            search_type=search_type,
            article_number=article_number,
            accepted=True,
            input_guard=input_guard,
            context_guard=context_guard,
        )

    # ========================================================
    # Grounded generation prompt
    # ========================================================

    def _build_prompt(
        self,
        query: str,
        context: str,
    ) -> str:

        return f"""
أنت مساعد قانوني متخصص في القانون المدني المصري.

مهمتك هي الإجابة عن سؤال المستخدم باستخدام المعلومات
الواردة في المستندات القانونية المسترجعة فقط.

قواعد إلزامية:

1. استخدم فقط المعلومات الموجودة في السياق.
2. لا تستخدم معلومات من معرفتك العامة أو من خارج السياق.
3. لا تخترع أي حكم قانوني أو شرط أو مادة قانونية.
4. لا تنسب إلى القانون نصاً غير موجود في المستندات.
5. كل نتيجة أو قاعدة قانونية في الإجابة يجب أن تكون مدعومة
   بمستند واحد أو أكثر من المستندات المسترجعة.
6. اذكر رقم المادة عند الاستناد إلى نص قانوني.
7. إذا كانت المستندات لا تحتوي على معلومات كافية للإجابة،
   قل بوضوح:
   "لا تتوفر معلومات كافية في السياق المسترجع للإجابة
   عن هذا السؤال بشكل كامل."
8. لا تغيّر موضوع السؤال.
9. لا تضف أمثلة أو نصائح من خارج السياق.
10. إذا كانت بعض المستندات غير مرتبطة مباشرة بالسؤال،
    تجاهلها ولا تحاول استخدامها لإكمال الإجابة.
11. لا تخمّن أو تستنتج قاعدة قانونية غير مذكورة صراحةً
    في المستندات.
12. لا تذكر معلومات طبية أو تجارية أو جنائية أو أي موضوع
    آخر غير متعلق بالسؤال إلا إذا ورد صراحةً في السياق.
13. فضّل إعادة صياغة النص القانوني الموجود في المستندات
    بدلاً من إنشاء شرح قانوني من خارجها.

السؤال:
{query}

المستندات القانونية المسترجعة:
<context>
{context}
</context>

أجب باللغة العربية.

قبل تقديم الإجابة، تحقق داخلياً من أن كل قاعدة قانونية
ذكرتها مدعومة فعلاً بالنص الموجود في السياق.

إذا لم يكن السياق كافياً، لا تخمّن.
""".strip()

    # ========================================================
    # Answer generation
    # ========================================================
    def answer(self, query: str) -> str:
        """Answer a question and trace the RAG execution in Langfuse."""

        langfuse = get_langfuse_client()

        # Keep the RAG application usable when tracing is disabled.
        if langfuse is None:
            return self._answer_without_tracing(query)

        with langfuse.start_as_current_observation(
            as_type="span",
            name="rag.ask",
            input={"question": query},
            metadata={
                "component": "egyptian-civil-code-rag",
                "retrieval_limit": str(self.retrieval_limit),
            },
        ) as root_span:

            with langfuse.start_as_current_observation(
                as_type="span",
                name="rag.retrieval",
                input={"question": query},
            ) as retrieval_span:
                retrieval = self.retrieve_legal_documents(query)

                source_articles = [
                    str((document.payload or {}).get("law_number", ""))
                    for document in retrieval.results
                    if (document.payload or {}).get("law_number")
                ]

                retrieval_span.update(
                    output={
                        "accepted": retrieval.accepted,
                        "search_type": retrieval.search_type,
                        "result_count": len(retrieval.results),
                        "source_articles": source_articles,
                        "refusal_reason": retrieval.refusal_reason,
                    }
                )

            if not retrieval.accepted:
                answer = (
                    retrieval.refusal_reason
                    or "Unable to process the request."
                )

                root_span.update(
                    output={
                        "answer": answer,
                        "sources": source_articles,
                        "status": "rejected",
                    }
                )
                return answer

            if not retrieval.results:
                answer = (
                    "لم يتم العثور على سياق قانوني "
                    "مناسب للإجابة عن السؤال."
                )

                root_span.update(
                    output={
                        "answer": answer,
                        "sources": [],
                        "status": "no_context",
                    }
                )
                return answer

            context = self._build_context(retrieval.results)
            prompt = self._build_prompt(
                query=query,
                context=context,
            )

            with langfuse.start_as_current_observation(
                as_type="generation",
                name="rag.answer_generation",
                model=getattr(
                    self.chat_model,
                    "model_name",
                    os.getenv(
                        "CHATBOT_MODEL",
                        "unknown",
                    ),
                ),
                input={
                    "question": query,
                    "context_document_count": len(retrieval.results),
                },
            ) as generation:
                answer = self.chat_model.invoke(prompt).strip()

                generation.update(
                    output=answer,
                )

            root_span.update(
                output={
                    "answer": answer,
                    "sources": source_articles,
                    "status": "success",
                },
                metadata={
                    "search_type": retrieval.search_type,
                    "source_count": str(len(source_articles)),
                },
            )
            return answer

    def _answer_without_tracing(self, query: str) -> str:
        """Original RAG answer flow, without observability dependencies."""
        retrieval = self.retrieve_legal_documents(query)
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
        context = self._build_context(retrieval.results)
        prompt = self._build_prompt(
            query=query,
            context=context,
        )
        return self.chat_model.invoke(prompt).strip()

# ============================================================
# Serialization
# ============================================================

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
