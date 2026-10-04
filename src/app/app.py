from __future__ import annotations

import os

import streamlit as st
from dotenv import load_dotenv

from clients import VectorDBClientWrapper
from models.chat import ChatBotLlmModel
from models.embedding import EmbeddingModel
from models.guard import GuardModel
from services.rag import RAG


load_dotenv()

QDRANT_HOST = os.getenv(
    "QDRANT_HOST",
    "localhost",
)
QDRANT_PORT = int(
    os.getenv(
        "QDRANT_PORT",
        "6333",
    )
)
QDRANT_COLLECTION = os.getenv(
    "QDRANT_COLLECTION",
    "test_qwen_embeddings",
)


@st.cache_resource
def get_rag() -> RAG:
    """
    Create the RAG service once per Streamlit process.
    """
    guard_model = GuardModel()
    embedding_model = EmbeddingModel()
    vector_db = VectorDBClientWrapper(
        url=f"http://{QDRANT_HOST}:{QDRANT_PORT}",
        collection_name=QDRANT_COLLECTION,
    )
    llm_model = ChatBotLlmModel()
    return RAG(
        guard_model=guard_model,
        embedding_model=embedding_model,
        vector_db=vector_db,
        llm_model=llm_model,
    )


def render_result(
    result,
    search_type: str,
    index: int,
) -> None:
    payload = getattr(
        result,
        "payload",
        None,
    ) or {}
    score = getattr(
        result,
        "score",
        None,
    )
    with st.container():
        if search_type == "exact_article":

            st.markdown(
                f"### 📜 "
                f"{payload.get('law_number', 'Article')}"
            )
        else:

            st.markdown(
                f"### Result {index}"
            )
            if score is not None:
                st.caption(
                    f"Similarity score: {score:.4f}"
                )
        title = payload.get("title")
        if title:
            st.markdown(
                f"**Location:** {title}"
            )
        content = payload.get("content")
        if content:
            st.markdown(content)
        st.divider()


def render_response(response) -> None:
    """
    Render a RAGResponse in Streamlit.
    """
    st.markdown(response.answer)
    if response.results:
        for index, result in enumerate(
            response.results,
            start=1,
        ):
            render_result(
                result=result,
                search_type=response.search_type or "semantic",
                index=index,
            )


st.set_page_config(
    page_title="Egyptian Law 131",
    page_icon="⚖️",
    layout="centered",
)
st.title("⚖️ Egyptian Civil Code")
st.caption(
    "Law No. 131 — RAG Legal Assistant"
)
rag = get_rag()
with st.sidebar:
    st.header("RAG Configuration")
    st.caption(
        f"Collection: `{QDRANT_COLLECTION}`"
    )
    st.caption(
        f"Qdrant: `{QDRANT_HOST}:{QDRANT_PORT}`"
    )
    st.divider()
    st.markdown("### Search modes")
    st.markdown(
        """
**Exact article**

`ما هي المادة ١؟`

Retrieves the specified article directly.

**Semantic search**

`ما هي شروط صحة العقد؟`

Uses the embedding model and Qdrant
to find relevant legal articles.
"""
    )
    st.divider()
    st.markdown("### Guard pipeline")
    st.markdown(
        """
1. User input
2. Qwen3Guard
3. Embedding
4. Qdrant retrieval
5. Context guard
6. LLM
7. Output guard
"""
    )

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(
        message["role"]
    ):
        st.markdown(
            message["content"]
        )
        if (
            message["role"] == "assistant"
            and "response" in message
        ):
            render_response(
                message["response"]
            )

query = st.chat_input(
    "Ask about Egyptian Civil Code..."
)
if query:
    st.session_state.messages.append(
        {
            "role": "user",
            "content": query,
        }
    )
    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner(
            "Checking and searching the law..."
        ):
            try:
                response = rag.invoke(query)
                render_response(response)
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": response.answer,
                        "response": response,
                    }
                )

            except Exception as exc:
                error_message = (
                    "An error occurred while processing "
                    "your request."
                )
                st.error(error_message)
                st.exception(exc)
