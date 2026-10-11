import os

import streamlit as st
from dotenv import load_dotenv

from app.clients.vector_db_client import VectorDBClientWrapper
from app.models.chat import ChatBotLlmModel
from app.models.embedding import EmbeddingModel
from app.models.guard import GuardModel
from app.services.rag import RAG, serialize_result


load_dotenv()


QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = os.getenv("QDRANT_PORT", "6333")
QDRANT_COLLECTION = os.getenv(
    "QDRANT_COLLECTION",
    "test_qwen_embeddings",
)


# ============================================================
# Cached dependencies
# ============================================================

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


# ============================================================
# Rendering helpers
# ============================================================

def render_retrieved_documents(results):
    """Display the legal documents supporting an answer."""

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

            heading = str(
                law_number or "Legal provision"
            )

            if title:
                heading += f" — {title}"

            st.markdown(f"**{heading}**")

            if score is not None:
                st.caption(
                    f"Retrieval score: {score:.4f}"
                )

            st.markdown(
                content or "No document text available."
            )

            st.divider()


def render_message(message):
    """Render a message and its associated retrieved documents."""

    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        if message["role"] == "assistant":
            render_retrieved_documents(
                message.get("results", [])
            )


def generate_answer(rag, query):
    """
    Retrieve legal documents and generate an answer through
    the RAG service's existing Arabic legal prompt.

    Returns:
        tuple[str, list[dict], str, bool]
    """

    response = rag.retrieve_legal_documents(query)

    # --------------------------------------------------------
    # Rejected input or context
    # --------------------------------------------------------

    if not response.accepted:
        if response.search_type == "guard_rejected_input":
            answer = (
                "لا يمكنني معالجة هذا السؤال "
                "وفقاً لنتيجة فحص السلامة."
            )

        elif response.search_type == "guard_rejected_context":
            answer = (
                "تعذّر استخدام النصوص المسترجعة "
                "بشكل آمن للإجابة عن السؤال."
            )

        else:
            answer = (
                "تعذّرت معالجة السؤال."
            )

        return (
            answer,
            [],
            response.search_type,
            False,
        )

    # --------------------------------------------------------
    # No retrieved documents
    # --------------------------------------------------------

    if not response.results:
        answer = (
            "لم يتم العثور على مواد قانونية مناسبة "
            "للإجابة عن السؤال."
        )

        return (
            answer,
            [],
            response.search_type,
            True,
        )

    # --------------------------------------------------------
    # Generate answer using the RAG service prompt
    # --------------------------------------------------------

    context = rag._build_context(
        response.results
    )

    prompt = rag._build_prompt(
        query=query,
        context=context,
    )

    answer = get_chat_model().invoke(
        prompt
    ).strip()

    if not answer:
        answer = (
            "تعذّر إنشاء إجابة. "
            "يرجى المحاولة مرة أخرى."
        )

    serialized_results = [
        serialize_result(result)
        for result in response.results
    ]

    return (
        answer,
        serialized_results,
        response.search_type,
        True,
    )


# ============================================================
# Main Streamlit application
# ============================================================

def main():
    st.set_page_config(
        page_title="Egyptian Civil Code",
        page_icon="⚖️",
        layout="wide",
    )

    st.title("Egyptian Civil Code")

    st.caption(
        "اسأل عن القانون المدني المصري. "
        "تُعرض المواد القانونية المسترجعة "
        "للمساعدة في مراجعة الإجابة."
    )

    # --------------------------------------------------------
    # Initialize conversation history
    # --------------------------------------------------------

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # --------------------------------------------------------
    # Sidebar
    # --------------------------------------------------------

    with st.sidebar:
        st.header("Conversation")

        if st.button(
            "Clear conversation",
            use_container_width=True,
        ):
            st.session_state.messages = []
            st.rerun()

        st.caption(
            "الإجابات تعتمد على النصوص المسترجعة "
            "من مجموعة البيانات القانونية."
        )

    # --------------------------------------------------------
    # Render conversation history
    # --------------------------------------------------------

    for message in st.session_state.messages:
        render_message(message)

    # --------------------------------------------------------
    # User input
    # --------------------------------------------------------

    query = st.chat_input(
        "اكتب سؤالك عن القانون المدني المصري..."
    )

    if not query or not query.strip():
        return

    query = query.strip()

    # --------------------------------------------------------
    # Display user message
    # --------------------------------------------------------

    st.session_state.messages.append(
        {
            "role": "user",
            "content": query,
        }
    )

    with st.chat_message("user"):
        st.markdown(query)

    # --------------------------------------------------------
    # Retrieve and answer
    # --------------------------------------------------------

    assistant_content = ""
    serialized_results = []
    search_type = "error"
    accepted = False

    with st.chat_message("assistant"):
        try:
            with st.spinner(
                "جارٍ البحث في مواد القانون المدني..."
            ):
                rag = get_rag()

                (
                    assistant_content,
                    serialized_results,
                    search_type,
                    accepted,
                ) = generate_answer(
                    rag=rag,
                    query=query,
                )

        except Exception:
            st.exception(
                Exception(
                    "حدث خطأ أثناء معالجة السؤال. "
                    "راجع سجلات التطبيق لمعرفة التفاصيل."
                )
            )

            assistant_content = (
                "حدث خطأ أثناء معالجة السؤال. "
                "يرجى التحقق من اتصال خدمة النموذج "
                "وقاعدة البيانات ثم المحاولة مجدداً."
            )

            serialized_results = []
            search_type = "error"
            accepted = False

        st.markdown(assistant_content)

        if serialized_results:
            render_retrieved_documents(
                serialized_results
            )

    # --------------------------------------------------------
    # Save assistant message
    # --------------------------------------------------------

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": assistant_content,
            "results": serialized_results,
            "search_type": search_type,
            "accepted": accepted,
        }
    )


if __name__ == "__main__":
    main()
