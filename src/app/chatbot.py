import os
import re

import requests
import streamlit as st
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Filter,
    FieldCondition,
    MatchValue,
)


# ============================================================
# Configuration
# ============================================================

EMBEDDING_URL = os.getenv(
    "EMBEDDING_URL",
    "http://localhost:8001/v1/embeddings",
)

EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "Qwen/Qwen3-Embedding-0.6B",
)

QDRANT_HOST = os.getenv(
    "QDRANT_HOST",
    "localhost",
)

QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))

COLLECTION_NAME = os.getenv(
    "QDRANT_COLLECTION",
    "test_qwen_embeddings",
)


# ============================================================
# Qdrant client
# ============================================================


@st.cache_resource
def get_qdrant_client():
    return QdrantClient(
        host=QDRANT_HOST,
        port=QDRANT_PORT,
    )


client = get_qdrant_client()


# ============================================================
# Arabic numeral normalization
# ============================================================

ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
WESTERN_DIGITS = "0123456789"

DIGIT_TRANSLATION = str.maketrans(
    ARABIC_DIGITS + PERSIAN_DIGITS,
    WESTERN_DIGITS + WESTERN_DIGITS,
)

WESTERN_TO_ARABIC = str.maketrans(
    WESTERN_DIGITS,
    ARABIC_DIGITS,
)


def normalize_digits(text: str) -> str:
    return text.translate(DIGIT_TRANSLATION)


# ============================================================
# Article number extraction
# ============================================================


def extract_article_number(query: str) -> int | None:
    normalized = normalize_digits(query)

    patterns = [
        r"\bالمادة\s*(\d+)\b",
        r"\bمادة\s*(\d+)\b",
        r"\barticle\s*#?\s*(\d+)\b",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            normalized,
            flags=re.IGNORECASE,
        )

        if match:
            return int(match.group(1))

    return None


# ============================================================
# Qwen embedding
# ============================================================


def get_embedding(text: str) -> list[float]:
    response = requests.post(
        EMBEDDING_URL,
        json={
            "model": EMBEDDING_MODEL,
            "input": text,
        },
        timeout=60,
    )

    response.raise_for_status()

    data = response.json()

    return data["data"][0]["embedding"]


# ============================================================
# Exact article search
# ============================================================


def search_article(article_number: int):
    arabic_number = str(article_number).translate(WESTERN_TO_ARABIC)

    law_number = f"مادة {arabic_number}"

    results = client.scroll(
        collection_name=COLLECTION_NAME,
        scroll_filter=Filter(
            must=[
                FieldCondition(
                    key="law_number",
                    match=MatchValue(value=law_number),
                )
            ]
        ),
        limit=1,
        with_payload=True,
        with_vectors=False,
    )[0]

    return results


# ============================================================
# Semantic search
# ============================================================


def semantic_search(
    query: str,
    limit: int = 5,
):
    query_embedding = get_embedding(query)

    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_embedding,
        limit=limit,
        with_payload=True,
    ).points

    return results


# ============================================================
# Query router
# ============================================================


def search(
    query: str,
    limit: int = 5,
):
    article_number = extract_article_number(query)

    if article_number is not None:
        return {
            "search_type": "exact_article",
            "article_number": article_number,
            "results": search_article(article_number),
        }

    return {
        "search_type": "semantic",
        "article_number": None,
        "results": semantic_search(
            query,
            limit,
        ),
    }


# ============================================================
# Result rendering
# ============================================================


def render_result(
    result,
    search_type: str,
    index: int,
):
    payload = result.payload or {}

    score = getattr(
        result,
        "score",
        None,
    )

    with st.container():
        # Result header
        if search_type == "exact_article":
            st.markdown(f"### 📜 {payload.get('law_number', 'Article')}")

        else:
            st.markdown(f"### Result {index}")

            if score is not None:
                st.caption(f"Similarity score: {score:.4f}")

        # Legal hierarchy
        title = payload.get("title")

        if title:
            st.markdown(f"**Location:** {title}")

        # Content
        content = payload.get("content")

        if content:
            st.markdown(content)

        st.divider()


# ============================================================
# Streamlit page configuration
# ============================================================

st.set_page_config(
    page_title="Egyptian Law 131",
    page_icon="⚖️",
    layout="centered",
)


# ============================================================
# Header
# ============================================================

st.title("⚖️ Egyptian Civil Code")
st.caption("Law No. 131 — Semantic & Article Search")


# ============================================================
# Sidebar
# ============================================================

with st.sidebar:
    st.header("Search")

    limit = st.slider(
        "Number of results",
        min_value=1,
        max_value=10,
        value=5,
    )

    st.divider()

    st.markdown("### Search modes")

    st.markdown(
        """
        **Exact article**

        `ما هي المادة ١؟`

        Finds the exact article directly.

        **Semantic search**

        `ما هي شروط صحة العقد؟`

        Uses Qwen embeddings to find
        semantically relevant articles.
        """
    )

    st.divider()

    st.caption(f"Collection: `{COLLECTION_NAME}`")

    st.caption(f"Embedding: `{EMBEDDING_MODEL}`")


# ============================================================
# Chat history
# ============================================================

if "messages" not in st.session_state:
    st.session_state.messages = []


# ============================================================
# Display previous messages
# ============================================================

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        # Render retrieved documents
        if message["role"] == "assistant" and "results" in message:
            search_type = message["search_type"]

            for index, result in enumerate(
                message["results"],
                start=1,
            ):
                render_result(
                    result,
                    search_type,
                    index,
                )


# ============================================================
# Chat input
# ============================================================

query = st.chat_input("Ask about Egyptian Civil Code...")


if query:
    # --------------------------------------------------------
    # Store user message
    # --------------------------------------------------------

    st.session_state.messages.append(
        {
            "role": "user",
            "content": query,
        }
    )

    # Display user message immediately

    with st.chat_message("user"):
        st.markdown(query)

    # --------------------------------------------------------
    # Search
    # --------------------------------------------------------

    with st.chat_message("assistant"):
        with st.spinner("Searching the law..."):
            try:
                search_result = search(
                    query,
                    limit=limit,
                )

                results = search_result["results"]

                search_type = search_result["search_type"]

                # ------------------------------------------------
                # No results
                # ------------------------------------------------

                if not results:
                    response_text = (
                        "I couldn't find a matching "
                        "article in the database."
                    )

                    st.markdown(response_text)

                # ------------------------------------------------
                # Exact article
                # ------------------------------------------------

                elif search_type == "exact_article":
                    article_number = search_result["article_number"]

                    response_text = f"Found Article " f"{article_number}."

                    st.markdown(response_text)

                    for index, result in enumerate(
                        results,
                        start=1,
                    ):
                        render_result(
                            result,
                            search_type,
                            index,
                        )

                # ------------------------------------------------
                # Semantic search
                # ------------------------------------------------

                else:
                    response_text = (
                        f"I found {len(results)} "
                        "potentially relevant articles."
                    )

                    st.markdown(response_text)

                    for index, result in enumerate(
                        results,
                        start=1,
                    ):
                        render_result(
                            result,
                            search_type,
                            index,
                        )

                # ------------------------------------------------
                # Store assistant response
                # ------------------------------------------------

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": response_text,
                        "results": results,
                        "search_type": search_type,
                    }
                )

            except requests.RequestException as exc:
                error = "The embedding service could " "not be reached."

                st.error(error)

                st.exception(exc)

            except Exception as exc:
                error = "An error occurred while " "searching Qdrant."

                st.error(error)

                st.exception(exc)
