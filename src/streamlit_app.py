import os

import streamlit as st
from dotenv import load_dotenv

from app.clients.vector_db_client import VectorDBClientWrapper
from app.models.embedding import EmbeddingModel
from app.models.guard import GuardModel
from app.services.rag import RAG, serialize_result


load_dotenv()


QDRANT_HOST = os.getenv("QDRANT_HOST")
QDRANT_PORT = os.getenv("QDRANT_PORT")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION")


@st.cache_resource
def get_embedding_model():
    return EmbeddingModel()


@st.cache_resource
def get_guard_model():
    return GuardModel()


@st.cache_resource
def get_vector_db():
    return VectorDBClientWrapper(
        url=f"http://{QDRANT_HOST}:{QDRANT_PORT}",
        collection_name=QDRANT_COLLECTION,
    )


@st.cache_resource
def get_rag():
    return RAG(
        embedding_model=get_embedding_model(),
        vector_db=get_vector_db(),
        guard_model=get_guard_model(),
        retrieval_limit=5,
    )


def render_message(message):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        if message["role"] != "assistant":
            return

        results = message.get("results", [])

        for result in results:
            law_number = result.get("law_number")
            title = result.get("title")
            content = result.get("content")
            score = result.get("score")

            with st.expander(
                f"{law_number} — {title or 'Article'}"
            ):
                if score is not None:
                    st.caption(
                        f"Retrieval score: {score:.4f}"
                    )

                st.markdown(content)


def main():
    st.set_page_config(
        page_title="Egyptian Civil Code",
        page_icon="⚖️",
        layout="wide",
    )

    st.title("Egyptian Civil Code")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    with st.sidebar:
        st.header("Conversation")

        if st.button(
            "Clear conversation",
            use_container_width=True,
        ):
            st.session_state.messages = []
            st.rerun()

    for message in st.session_state.messages:
        render_message(message)

    query = st.chat_input(
        "Ask a question about the Egyptian Civil Code..."
    )

    if not query:
        return

    # ---------------------------------------------------------
    # User message
    # ---------------------------------------------------------

    user_message = {
        "role": "user",
        "content": query,
    }

    st.session_state.messages.append(user_message)

    with st.chat_message("user"):
        st.markdown(query)

    # ---------------------------------------------------------
    # RAG
    # ---------------------------------------------------------

    rag = get_rag()

    with st.spinner(
        "Checking request and searching the "
        "Egyptian Civil Code..."
    ):
        response = rag.retrieve_legal_documents(query)

    # ---------------------------------------------------------
    # Handle rejected request
    # ---------------------------------------------------------

    if not response.accepted:
        if response.search_type == "guard_rejected_input":
            assistant_content = (
                "I can't assist with that request."
            )

        elif response.search_type == "guard_rejected_context":
            assistant_content = (
                "The retrieved content could not be "
                "safely used for this request."
            )

        else:
            assistant_content = (
                "The request could not be processed safely."
            )

        serialized_results = []

    # ---------------------------------------------------------
    # Handle accepted request
    # ---------------------------------------------------------

    else:
        serialized_results = [
            serialize_result(result)
            for result in response.results
        ]

        if not serialized_results:
            assistant_content = (
                "No relevant legal articles were found."
            )

        elif response.search_type == "exact_article":
            assistant_content = (
                f"Found Article "
                f"{response.article_number}."
            )

        else:
            assistant_content = (
                "Relevant legal articles were found."
            )

    # ---------------------------------------------------------
    # Assistant message
    # ---------------------------------------------------------

    assistant_message = {
        "role": "assistant",
        "content": assistant_content,
        "results": serialized_results,
        "search_type": response.search_type,
        "article_number": response.article_number,
        "accepted": response.accepted,
    }

    st.session_state.messages.append(
        assistant_message
    )

    st.rerun()


if __name__ == "__main__":
    main()