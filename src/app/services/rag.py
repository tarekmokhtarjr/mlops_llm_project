from dataclasses import dataclass, field
from typing import List, Optional
from .. clients.vector_db_client import VectorDBClientWrapper
from ..models.chat import ChatBotLlmModel
from ..models.embedding import EmbeddingModel
from ..models.guard import GuardModel

@dataclass
class RAGResponse:
    answer: str
    accepted: bool
    refusal: bool = False
    refusal_reason: Optional[str] = None
    sources: List[dict] = field(default_factory=list)

    # Useful later for MLflow / RAGAS / Langfuse
    query: Optional[str] = None
    retrieved_context: List[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class RAGService:

    def __init__(
        self,
        guard_model,
        embedding_model,
        llm_model,
        vector_db,
        guardrails=None,
    ):
        self.guard_model = guard_model
        self.embedding_model = embedding_model
        self.llm_model = llm_model
        self.vector_db = vector_db
        self.guardrails = guardrails

    def process(self, query: str) -> RAGResponse:
        """
        Execute the complete RAG pipeline.
        """
        input_guard_result = self._check_input(query)
        if not input_guard_result["accepted"]:
            return RAGResponse(
                answer=input_guard_result["message"],
                accepted=False,
                refusal=True,
                refusal_reason=input_guard_result.get("reason"),
                query=query,
            )
        embedding = self._embed_query(query)
        retrieved_documents = self._retrieve(embedding)
        context_guard_result = self._check_context(
            query=query,
            documents=retrieved_documents,
        )
        if not context_guard_result["accepted"]:
            return RAGResponse(
                answer=context_guard_result["message"],
                accepted=False,
                refusal=True,
                refusal_reason=context_guard_result.get("reason"),
                query=query,
                retrieved_context=[
                    doc.get("content", "")
                    for doc in retrieved_documents
                ],
            )
        context = self._build_context(retrieved_documents)
        answer = self._generate_answer(
            query=query,
            context=context,
        )
        return RAGResponse(
            answer=answer,
            accepted=True,
            refusal=False,
            query=query,
            retrieved_context=context,
            sources=retrieved_documents,
        )

    def _check_input(self, query: str) -> dict:
        if self.guardrails is not None:
            result = self.guardrails.validate_input(query)
            if not result["accepted"]:
                return result
        result = self.guard_model.check_input(query)
        return result

    def _embed_query(self, query: str):
        return self.embedding_model.embed_query(query)

    def _retrieve(self, embedding):
        return self.vector_db.search(
            vector=embedding,
        )

    def _check_context(self, query: str, documents: List[dict]) -> dict:
        context = "\n\n".join(
            doc.get("content", "")
            for doc in documents
        )
        if self.guardrails is not None:
            result = self.guardrails.validate_context(
                query=query,
                context=context,
            )
            if not result["accepted"]:
                return result
        result = self.guard_model.check(context)
        return result

    def _build_context(self, documents: List[dict]) -> List[str]:
        return [
            doc.get("content", "")
            for doc in documents
        ]

    def _generate_answer(self, query: str, context: List[str]):
        context_text = "\n\n".join(context)
        prompt = f"""
You are a legal assistant.

Answer the user's question using only the provided context.

If the context does not contain enough information to answer
the question, say that the available documents do not provide
enough information.

Context:
{context_text}

Question:
{query}

Answer:
"""
        return self.llm_model.generate(prompt)