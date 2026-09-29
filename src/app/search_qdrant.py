import os
import re

import requests
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
# Qdrant
# ============================================================

client = QdrantClient(
    host=QDRANT_HOST,
    port=QDRANT_PORT,
)


# ============================================================
# Arabic numeral normalization
# ============================================================

ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
WESTERN_DIGITS = "0123456789"

DIGIT_TRANSLATION = str.maketrans(
    ARABIC_DIGITS,
    WESTERN_DIGITS + WESTERN_DIGITS,
)


def normalize_digits(text: str) -> str:
    """
    Convert Arabic/Persian digits to Western digits.

    Example:
        مادة ١٤٧ -> مادة 147
        مادة ۱۴۷ -> مادة 147
    """
    return text.translate(DIGIT_TRANSLATION)


# ============================================================
# Article number extraction
# ============================================================


def extract_article_number(query: str) -> int | None:
    """
    Detect an explicit article number in a user query.

    Examples:

        "مادة ١"
        "المادة ١"
        "ما هي المادة ١؟"
        "نص المادة 147"
        "Article 147"

    Returns:
        int | None
    """

    normalized = normalize_digits(query)

    patterns = [
        # Arabic
        r"\bالمادة\s*(\d+)\b",
        r"\bمادة\s*(\d+)\b",
        # English
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
    """
    Generate an embedding using the OpenAI-compatible
    Qwen embedding endpoint.
    """

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
    """
    Exact lookup using the law_number field.

    Your current payload looks like:

        {
            "law_number": "مادة ١",
            "content": "...",
            "title": "..."
        }

    Therefore we search for:

        law_number == "مادة ١"
    """

    # Convert:
    #
    # 1 -> ١
    # 147 -> ١٤٧
    #
    # because your database currently stores Arabic numerals.

    arabic_number = str(article_number).translate(
        str.maketrans(
            WESTERN_DIGITS,
            ARABIC_DIGITS,
        )
    )

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


def semantic_search(query: str, limit: int = 5):
    """
    Generate a Qwen embedding and perform semantic
    similarity search in Qdrant.
    """

    query_embedding = get_embedding(query)

    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_embedding,
        limit=limit,
        with_payload=True,
    ).points

    return results


# ============================================================
# Natural-language search router
# ============================================================


def search(query: str, limit: int = 5):
    """
    Main search function.

    The user can provide a completely natural question.

    Example:

        "ما هي المادة ١؟"

    -> Exact article lookup.

    Example:

        "ما هي شروط صحة العقد؟"

    -> Semantic vector search.
    """

    article_number = extract_article_number(query)

    # --------------------------------------------------------
    # Exact article query
    # --------------------------------------------------------

    if article_number is not None:
        print(f"[Router] Detected article number: " f"{article_number}")

        results = search_article(article_number)

        return {
            "search_type": "exact_article",
            "article_number": article_number,
            "results": results,
        }

    # --------------------------------------------------------
    # Semantic query
    # --------------------------------------------------------

    print("[Router] No article number detected.")
    print("[Router] Using semantic vector search.")

    results = semantic_search(
        query,
        limit=limit,
    )

    return {
        "search_type": "semantic",
        "article_number": None,
        "results": results,
    }


# ============================================================
# Pretty printing
# ============================================================


def print_results(search_result):
    """
    Display search results in a human-readable format.
    """

    search_type = search_result["search_type"]
    results = search_result["results"]

    print()
    print("=" * 70)

    print(f"Search type: {search_type}")

    if search_result["article_number"] is not None:
        print(f"Article number: " f"{search_result['article_number']}")

    print("=" * 70)

    if not results:
        print("No results found.")
        return

    for index, result in enumerate(results, start=1):
        print()
        print(f"--- Result {index} ---")

        # Exact search returns ScoredPoint only for vector
        # searches, while scroll returns Record objects.
        score = getattr(result, "score", None)

        if score is not None:
            print(f"Score: {score:.6f}")

        payload = result.payload or {}

        print(f"Law Number: " f"{payload.get('law_number')}")

        print(f"Title: " f"{payload.get('title')}")

        print(f"Content: " f"{payload.get('content')}")

    print()


# ============================================================
# Interactive CLI
# ============================================================


def main():
    print("=" * 70)
    print("Egyptian Law 131 - Qdrant Search")
    print("=" * 70)
    print()
    print("Examples:")
    print("  ما هي المادة ١؟")
    print("  ما هو نص المادة 147؟")
    print("  ما هي شروط صحة العقد؟")
    print("  ماذا يحدث عند الإخلال بالعقد؟")
    print()
    print("Type 'exit' to quit.")
    print()

    while True:
        query = input("Search: ").strip()

        if not query:
            continue

        if query.lower() in {"exit", "quit"}:
            break

        try:
            result = search(query)

            print_results(result)

        except requests.RequestException as exc:
            print()
            print(f"Embedding API error: {exc}")

        except Exception as exc:
            print()
            print(f"Search error: {exc}")


if __name__ == "__main__":
    main()
