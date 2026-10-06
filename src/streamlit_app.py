import os
import re

import streamlit as st
from dotenv import load_dotenv

from app.clients.vector_db_client import (
    VectorDBClientWrapper,
)
from app.models.embedding import EmbeddingModel
from app.services.retrieval import (
    hybrid_search,
    lexical_search,
)


load_dotenv()


# ============================================================
# Configuration
# ============================================================

QDRANT_HOST = os.getenv(
    "QDRANT_HOST",
    "localhost",
)

QDRANT_PORT = os.getenv(
    "QDRANT_PORT",
    "6333",
)

QDRANT_COLLECTION = os.getenv(
    "QDRANT_COLLECTION",
    "test_qwen_embeddings",
)


# ============================================================
# Arabic / Western digit conversion
# ============================================================

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


def normalize_digits(
    text: str,
) -> str:
    return text.translate(
        ARABIC_TO_WESTERN
    )


# ============================================================
# Article detection
# ============================================================

def extract_article_number(
    query: str,
) -> int | None:

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


# ============================================================
# Resources
# ============================================================

@st.cache_resource
def get_embedding_model():
    return EmbeddingModel()


@st.cache_resource
def get_vector_db():

    return VectorDBClientWrapper(
        url=(
            f"http://"
            f"{QDRANT_HOST}:"
            f"{QDRANT_PORT}"
        ),
        collection_name=QDRANT_COLLECTION,
    )


embedding_model = get_embedding_model()
vector_db = get_vector_db()


# ============================================================
# Session state
# ============================================================

if "messages" not in st.session_state:

    st.session_state.messages = []


# ============================================================
# Legal retrieval
# ============================================================

def retrieve_legal_documents(
    query: str,
    limit: int = 5,
) -> dict:

    # --------------------------------------------------------
    # Exact article detection
    # --------------------------------------------------------

    article_number = (
        extract_article_number(
            query
        )
    )

    if article_number is not None:

        law_number = (
            article_number_to_law_number(
                article_number
            )
        )

        results = (
            vector_db.search_article(
                law_number=law_number
            )
        )

        return {
            "search_type": "exact_article",
            "article_number": article_number,
            "law_number": law_number,
            "results": results,
        }

    # ========================================================
    # Hybrid retrieval
    # ========================================================

    # --------------------------------------------------------
    # Semantic retrieval
    #
    # Retrieve more candidates than we finally display.
    # This gives lexical ranking more candidates to work with.
    # --------------------------------------------------------

    query_vector = (
        embedding_model.embed(
            query
        )
    )

    semantic_results = (
        vector_db.search(
            query_vector=query_vector,
            limit=max(
                limit * 4,
                20,
            ),
        )
    )

    # --------------------------------------------------------
    # Get documents for lexical retrieval
    # --------------------------------------------------------

    documents = (
        vector_db.get_all_documents()
    )

    lexical_results = lexical_search(
        query=query,
        documents=documents,
        limit=max(
            limit * 4,
            20,
        ),
    )

    # --------------------------------------------------------
    # Merge semantic + lexical
    # --------------------------------------------------------

    results = hybrid_search(
        query=query,
        semantic_results=semantic_results,
        lexical_results=lexical_results,
        limit=limit,
    )

    return {
        "search_type": "hybrid",
        "article_number": None,
        "law_number": None,
        "results": results,
    }


# ============================================================
# Serialize result
# ============================================================

def serialize_result(
    result,
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


# ============================================================
# Render result
# ============================================================

def render_result(
    result: dict,
    search_type: str,
    index: int,
):

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

    # --------------------------------------------------------
    # Exact article
    # --------------------------------------------------------

    if search_type == "exact_article":

        st.markdown(
            f"### 📜 {law_number or 'Article'}"
        )

    # --------------------------------------------------------
    # Semantic / hybrid
    # --------------------------------------------------------

    else:

        st.markdown(
            f"### المادة {index}"
        )

        if score is not None:

            st.caption(
                f"Similarity: {score:.4f}"
            )

    if title:

        st.markdown(
            f"**الموقع:** {title}"
        )

    if content:

        st.markdown(
            content
        )

    st.divider()


# ============================================================
# Page configuration
# ============================================================

st.set_page_config(
    page_title="Egyptian Civil Code",
    page_icon="⚖️",
    layout="wide",
)


# ============================================================
# Header
# ============================================================

st.title(
    "⚖️ Egyptian Civil Code"
)

st.caption(
    "RAG Assistant for Egyptian Civil Law No. 131"
)


# ============================================================
# Sidebar
# ============================================================

with st.sidebar:

    st.header(
        "⚙️ Retrieval Configuration"
    )

    result_limit = st.slider(
        "Number of retrieved articles",
        min_value=1,
        max_value=10,
        value=5,
    )

    st.divider()

    st.markdown(
        """
### Retrieval modes

**Specific article**

`ما هي المادة ١؟`

→ Exact article lookup

**Legal question**

`ما هي المواد المتعلقة بالملكية؟`

→ Hybrid retrieval

Hybrid retrieval combines:

- Semantic similarity
- Textual/keyword matching
        """
    )

    st.divider()

    st.caption(
        f"Qdrant collection: "
        f"`{QDRANT_COLLECTION}`"
    )

    st.caption(
        "Embedding model: "
        f"`{os.getenv('EMBEDDING_MODEL')}`"
    )

    st.divider()

    if st.button(
        "🗑️ Clear conversation",
        use_container_width=True,
    ):

        st.session_state.messages = []

        st.rerun()


# ============================================================
# Previous conversation
# ============================================================

for message in st.session_state.messages:

    if message["role"] == "user":

        with st.chat_message(
            "user"
        ):

            st.write(
                message["content"]
            )

    elif message["role"] == "assistant":

        with st.chat_message(
            "assistant"
        ):

            search_type = message.get(
                "search_type",
                "hybrid",
            )

            if search_type == "exact_article":

                st.caption(
                    "نوع البحث: "
                    "Exact Article Lookup"
                )

            elif search_type == "hybrid":

                st.caption(
                    "نوع البحث: "
                    "Hybrid Retrieval"
                )

            results = message.get(
                "results",
                [],
            )

            if not results:

                st.info(
                    "لم يتم العثور على مواد "
                    "مرتبطة بالسؤال."
                )

            else:

                for index, result in enumerate(
                    results,
                    start=1,
                ):

                    render_result(
                        result=result,
                        search_type=search_type,
                        index=index,
                    )


# ============================================================
# Chat input
# ============================================================

query = st.chat_input(
    "اسأل عن القانون المدني المصري رقم ١٣١..."
)


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

    # --------------------------------------------------------
    # Retrieve
    # --------------------------------------------------------

    try:

        with st.spinner(
            "جاري البحث في القانون المدني..."
        ):

            response = (
                retrieve_legal_documents(
                    query=query,
                    limit=result_limit,
                )
            )

    except Exception as exc:

        st.session_state.messages.append(
            {
                "role": "assistant",
                "search_type": "error",
                "results": [],
                "error": str(exc),
            }
        )

        st.rerun()

    # --------------------------------------------------------
    # Serialize results
    # --------------------------------------------------------

    stored_results = [
        serialize_result(
            result
        )
        for result in response[
            "results"
        ]
    ]

    # --------------------------------------------------------
    # Store assistant response
    # --------------------------------------------------------

    st.session_state.messages.append(
        {
            "role": "assistant",
            "search_type": response[
                "search_type"
            ],
            "article_number": response[
                "article_number"
            ],
            "law_number": response[
                "law_number"
            ],
            "results": stored_results,
        }
    )

    # --------------------------------------------------------
    # Render entire conversation again
    # --------------------------------------------------------

    st.rerun()