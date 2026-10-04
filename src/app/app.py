from __future__ import annotations

import logging
import os
import time
import uuid

import streamlit as st
from dotenv import load_dotenv

from app.clients.vector_db_client import VectorDBClientWrapper
from app.models.chat import ChatBotLlmModel
from app.models.embedding import EmbeddingModel
from app.models.guard import GuardModel
from app.services.rag import RAG


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

load_dotenv()

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
DEBUG_MODE = os.getenv("DEBUG", "0") == "1"

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


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format=(
        "%(asctime)s | "
        "%(levelname)-8s | "
        "%(name)s | "
        "%(message)s"
    ),
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Streamlit configuration
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Egyptian Law 131",
    page_icon="⚖️",
    layout="centered",
)


# ---------------------------------------------------------------------------
# Debug helpers
# ---------------------------------------------------------------------------

def log_stage(
    stage: str,
    message: str = "",
    request_id: str | None = None,
) -> None:
    """Log an application stage and optionally show it in debug mode."""

    prefix = (
        f"[{request_id}] "
        if request_id
        else ""
    )

    logger.info(
        "%s%s%s",
        prefix,
        stage,
        f" | {message}" if message else "",
    )

    if DEBUG_MODE:
        st.caption(
            f"DEBUG | {prefix}{stage}"
            f"{f' | {message}' if message else ''}"
        )


def log_exception(
    message: str,
    exc: Exception,
    request_id: str | None = None,
) -> None:
    """Log an exception with a complete traceback."""

    prefix = (
        f"[{request_id}] "
        if request_id
        else ""
    )

    logger.exception(
        "%s%s",
        prefix,
        message,
        exc_info=exc,
    )


# ---------------------------------------------------------------------------
# RAG initialization
# ---------------------------------------------------------------------------

@st.cache_resource
def get_rag() -> RAG:
    """
    Create the RAG service once per Streamlit process.

    All initialization steps are logged separately so that failures
    can be identified without guessing which component failed.
    """

    start_time = time.perf_counter()

    logger.info("RAG initialization started")

    try:
        logger.info("Creating GuardModel")
        guard_model = GuardModel()
        logger.info("GuardModel created successfully")

        logger.info("Creating EmbeddingModel")
        embedding_model = EmbeddingModel()
        logger.info("EmbeddingModel created successfully")

        qdrant_url = (
            f"http://{QDRANT_HOST}:{QDRANT_PORT}"
        )

        logger.info(
            "Creating VectorDBClientWrapper | "
            "url=%s | collection=%s",
            qdrant_url,
            QDRANT_COLLECTION,
        )

        vector_db = VectorDBClientWrapper(
            url=qdrant_url,
            collection_name=QDRANT_COLLECTION,
        )

        logger.info(
            "VectorDBClientWrapper created successfully"
        )

        logger.info("Creating ChatBotLlmModel")
        llm_model = ChatBotLlmModel()
        logger.info("ChatBotLlmModel created successfully")

        logger.info("Creating RAG service")

        rag = RAG(
            guard_model=guard_model,
            embedding_model=embedding_model,
            vector_db=vector_db,
            llm_model=llm_model,
        )

        elapsed = (
            time.perf_counter()
            - start_time
        )

        logger.info(
            "RAG initialization completed in %.2f seconds",
            elapsed,
        )

        return rag

    except Exception:
        elapsed = (
            time.perf_counter()
            - start_time
        )

        logger.exception(
            "RAG initialization FAILED after %.2f seconds"
            ,
        )

        logger.error(
            "RAG initialization failure details: "
            "Qdrant=%s:%s collection=%s",
            QDRANT_HOST,
            QDRANT_PORT,
            QDRANT_COLLECTION,
        )

        raise


# ---------------------------------------------------------------------------
# Response rendering
# ---------------------------------------------------------------------------

def render_result(
    result,
    search_type: str,
    index: int,
) -> None:
    """Render one retrieved search result."""

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
                search_type=(
                    response.search_type
                    or "semantic"
                ),
                index=index,
            )


# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------

st.title("⚖️ Egyptian Civil Code")

st.caption(
    "Law No. 131 — RAG Legal Assistant"
)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

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

    st.divider()

    st.markdown("### Debug")

    if DEBUG_MODE:
        st.success("Debug mode: ON")
        st.caption(
            f"Log level: `{LOG_LEVEL}`"
        )
    else:
        st.info("Debug mode: OFF")

    st.caption(
        "Set `DEBUG=1` to show debug stages."
    )


# ---------------------------------------------------------------------------
# Initialize RAG
# ---------------------------------------------------------------------------

try:
    log_stage(
        "RAG_INIT",
        "Starting RAG initialization",
    )

    rag = get_rag()

    log_stage(
        "RAG_INIT",
        "RAG initialization successful",
    )

except Exception as exc:

    logger.exception(
        "Application startup failed while "
        "initializing RAG"
    )

    st.error(
        "The RAG system could not be initialized."
    )

    if DEBUG_MODE:
        st.exception(exc)

    st.stop()


# ---------------------------------------------------------------------------
# Chat history
# ---------------------------------------------------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []


# ---------------------------------------------------------------------------
# Render previous messages
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Chat input
# ---------------------------------------------------------------------------

query = st.chat_input(
    "Ask about Egyptian Civil Code..."
)


# ---------------------------------------------------------------------------
# Process request
# ---------------------------------------------------------------------------

if query:

    request_id = uuid.uuid4().hex[:8]

    start_time = time.perf_counter()

    logger.info(
        "=" * 80
    )

    logger.info(
        "[%s] NEW CHAT REQUEST",
        request_id,
    )

    logger.info(
        "[%s] Query: %s",
        request_id,
        query,
    )

    # Store user message immediately.
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

                # -----------------------------------------------------------
                # RAG
                # -----------------------------------------------------------

                log_stage(
                    "RAG_CALL",
                    "Calling rag.invoke()",
                    request_id,
                )

                rag_start = time.perf_counter()

                response = rag.invoke(query)

                rag_elapsed = (
                    time.perf_counter()
                    - rag_start
                )

                log_stage(
                    "RAG_CALL",
                    (
                        "Completed successfully "
                        f"in {rag_elapsed:.2f}s"
                    ),
                    request_id,
                )

                # -----------------------------------------------------------
                # Response information
                # -----------------------------------------------------------

                result_count = len(
                    response.results
                    or []
                )

                logger.info(
                    "[%s] Search type: %s",
                    request_id,
                    response.search_type,
                )

                logger.info(
                    "[%s] Retrieved results: %d",
                    request_id,
                    result_count,
                )

                logger.info(
                    "[%s] Answer length: %d characters",
                    request_id,
                    len(response.answer or ""),
                )

                # -----------------------------------------------------------
                # Render response
                # -----------------------------------------------------------

                log_stage(
                    "RENDER",
                    "Rendering response",
                    request_id,
                )

                render_response(response)

                # -----------------------------------------------------------
                # Save assistant response
                # -----------------------------------------------------------

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": response.answer,
                        "response": response,
                    }
                )

                elapsed = (
                    time.perf_counter()
                    - start_time
                )

                logger.info(
                    "[%s] REQUEST COMPLETED in %.2f seconds",
                    request_id,
                    elapsed,
                )

            except Exception as exc:

                elapsed = (
                    time.perf_counter()
                    - start_time
                )

                logger.exception(
                    "[%s] REQUEST FAILED after %.2f seconds",
                    request_id,
                )

                st.error(
                    "An error occurred while processing "
                    "your request."
                )

                # Always show the actual exception when
                # debugging is enabled.
                if DEBUG_MODE:
                    st.exception(exc)

                else:
                    st.info(
                        "Run the application with "
                        "`DEBUG=1` to display the "
                        "full traceback."
                    )

    logger.info(
        "[%s] Request finished",
        request_id,
    )

    logger.info(
        "=" * 80
    )