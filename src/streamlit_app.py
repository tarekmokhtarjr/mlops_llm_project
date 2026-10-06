import os

import streamlit as st
from dotenv import load_dotenv

from app.clients.vector_db_client import VectorDBClientWrapper
from app.models.embedding import EmbeddingModel
from app.services.rag import RAG, serialize_result


load_dotenv()


QDRANT_HOST = os.getenv("QDRANT_HOST")
QDRANT_PORT = os.getenv("QDRANT_PORT")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION")


@st.cache_resource
def get_embedding_model():
    return EmbeddingModel()


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
        page_title="Egyptian Civil Code RAG",
        page_icon="⚖️",
        layout="wide",
    )

    st.title("Egyptian Civil Code RAG")

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

    # Render previous conversation
    for message in st.session_state.messages:
        render_message(message)

    query = st.chat_input(
        "Ask a question about the Egyptian Civil Code..."
    )

    if not query:
        return

    # Store and display user message
    user_message = {
        "role": "user",
        "content": query,
    }

    st.session_state.messages.append(user_message)

    with st.chat_message("user"):
        st.markdown(query)

    # Run RAG
    rag = get_rag()

    with st.spinner("Searching the Egyptian Civil Code..."):
        response = rag.retrieve_legal_documents(query)

    serialized_results = [
        serialize_result(result)
        for result in response.results
    ]

    # Build assistant response
    if not serialized_results:
        assistant_content = (
            "No relevant legal articles were found."
        )

    elif response.search_type == "exact_article":
        assistant_content = (
            f"Found Article {response.article_number}."
        )

    else:
        assistant_content = (
            "Relevant legal articles were found."
        )

    # Store complete assistant message.
    # Retrieval results belong to this specific message,
    # so they survive Streamlit reruns.
    assistant_message = {
        "role": "assistant",
        "content": assistant_content,
        "results": serialized_results,
        "search_type": response.search_type,
        "article_number": response.article_number,
    }

    st.session_state.messages.append(assistant_message)

    # Rerender the complete conversation from session state.
    st.rerun()


if __name__ == "__main__":
    main()