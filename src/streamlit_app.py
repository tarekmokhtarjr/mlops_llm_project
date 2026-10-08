import os

import streamlit as st
from dotenv import load_dotenv

from app.clients.vector_db_client import VectorDBClientWrapper
from app.models.chat import ChatBotLlmModel
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
def get_chat_model():
    return ChatBotLlmModel()


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
        chat_model=get_chat_model(),
        retrieval_limit=5,
    )


def render_message(message):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        if message["role"] != "assistant":
            return

        results = message.get("results", [])

        if not results:
            return

        with st.expander(
            f"Retrieved Documents ({len(results)})"
        ):
            for result in results:
                law_number = result.get("law_number")
                title = result.get("title")
                content = result.get("content")
                score = result.get("score")

                st.markdown(
                    f"**{law_number} — "
                    f"{title or 'Article'}**"
                )

                if score is not None:
                    st.caption(
                        f"Retrieval score: {score:.4f}"
                    )

                st.markdown(content)

                st.divider()


def main():
    st.set_page_config(
        page_title="Egyptian Civil Code",
        page_icon="⚖️",
        layout="wide",
    )

    st.title("Egyptian Civil Code")

    st.caption(
        "Ask questions about the Egyptian Civil Code."
    )

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

    # ---------------------------------------------------------
    # Render conversation history
    # ---------------------------------------------------------

    for message in st.session_state.messages:
        render_message(message)

    # ---------------------------------------------------------
    # User input
    # ---------------------------------------------------------

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

    st.session_state.messages.append(
        user_message
    )

    with st.chat_message("user"):
        st.markdown(query)

    # ---------------------------------------------------------
    # RAG + LLM
    # ---------------------------------------------------------

    rag = get_rag()

    with st.chat_message("assistant"):

        with st.spinner(
            "Searching the Egyptian Civil Code "
            "and generating an answer..."
        ):
            response = rag.retrieve_legal_documents(
                query
            )

            # -------------------------------------------------
            # Handle rejected request
            # -------------------------------------------------

            if not response.accepted:

                if (
                    response.search_type
                    == "guard_rejected_input"
                ):
                    assistant_content = (
                        "I can't assist with that request."
                    )

                elif (
                    response.search_type
                    == "guard_rejected_context"
                ):
                    assistant_content = (
                        "The retrieved content could not "
                        "be safely used for this request."
                    )

                else:
                    assistant_content = (
                        "The request could not be "
                        "processed safely."
                    )

                serialized_results = []

            # -------------------------------------------------
            # Handle no results
            # -------------------------------------------------

            elif not response.results:

                assistant_content = (
                    "No relevant legal articles were found."
                )

                serialized_results = []

            # -------------------------------------------------
            # Generate LLM answer
            # -------------------------------------------------

            else:

                # Build the answer from the already retrieved
                # and context-guarded documents.
                context_parts = []

                for index, result in enumerate(
                    response.results,
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

                context = "\n\n".join(
                    context_parts
                )

                prompt = f"""
You are a legal information assistant.

Answer the user's question using ONLY the
provided Egyptian Civil Code context.

Rules:
- Do not invent legal provisions or facts.
- Do not use information outside the provided context.
- If the context does not contain enough information,
  clearly say that there is insufficient information.
- When relevant, mention the article number supporting
  the answer.
- Give a concise and direct answer.

User question:
{query}

Retrieved context:
<context>
{context}
</context>

Answer:
""".strip()

                assistant_content = (
                    get_chat_model().invoke(prompt)
                )

                serialized_results = [
                    serialize_result(result)
                    for result in response.results
                ]

        # -----------------------------------------------------
        # Display answer
        # -----------------------------------------------------

        st.markdown(
            assistant_content
        )

        # -----------------------------------------------------
        # Display retrieved documents
        # -----------------------------------------------------

        if serialized_results:

            with st.expander(
                f"Retrieved Documents "
                f"({len(serialized_results)})"
            ):

                for result in serialized_results:

                    law_number = result.get(
                        "law_number"
                    )

                    title = result.get(
                        "title"
                    )

                    content = result.get(
                        "content"
                    )

                    score = result.get(
                        "score"
                    )

                    st.markdown(
                        f"**{law_number} — "
                        f"{title or 'Article'}**"
                    )

                    if score is not None:
                        st.caption(
                            f"Retrieval score: "
                            f"{score:.4f}"
                        )

                    st.markdown(content)

                    st.divider()

    # ---------------------------------------------------------
    # Store assistant message
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


if __name__ == "__main__":
    main()
