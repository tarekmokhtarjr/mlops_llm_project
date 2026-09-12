import json
import requests
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
)

EMBEDDING_URL = "http://localhost:8001/v1/embeddings"
MODEL = "Qwen/Qwen3-Embedding-0.6B"

QDRANT_HOST = "localhost"
QDRANT_PORT = 6333

COLLECTION_NAME = "test_qwen_embeddings"

def get_embedding(text: str) -> list[float]:
    response = requests.post(
        EMBEDDING_URL,
        json={
            "model": MODEL,
            "input": text,
        },
        timeout=60,
    )

    response.raise_for_status()

    data = response.json()

    embedding = data["data"][0]["embedding"]

    print(f"{text} Embedding dimension: {len(embedding)}")

    return embedding

def main():
    # ---------------------------------------------------------
    # 1. Read JSON data from the file
    # ---------------------------------------------------------
    with open("data/egyptian_civil_law_131_1948.json", "r", encoding="utf-8") as file:
        data = json.load(file)

    # ---------------------------------------------------------
    # 2. Connect to Qdrant
    # ---------------------------------------------------------
    client = QdrantClient(
        host=QDRANT_HOST,
        port=QDRANT_PORT,
    )

    # ---------------------------------------------------------
    # 3. Recreate test collection
    # ---------------------------------------------------------
    if client.collection_exists(COLLECTION_NAME):
        client.delete_collection(COLLECTION_NAME)

    vector_size = None
    points = []

    for id, item in enumerate(data, start=1):
        content = item["content"]
        embedding = get_embedding(content)

        if vector_size is None:
            vector_size = len(embedding)

        points.append(
            PointStruct(
                id=id,
                vector=embedding,
                payload={
                    "law_number": item.get("law_number"),
                    "title": item.get("title"),
                    "content": content,
                },
            )
        )

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=vector_size,
            distance=Distance.COSINE,
        ),
    )

    print(f"Created collection: {COLLECTION_NAME}")

    # ---------------------------------------------------------
    # 4. Store embeddings
    # ---------------------------------------------------------
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=points,
    )

    print("Embeddings stored successfully.")

    # ---------------------------------------------------------
    # 5. Search using another query
    # ---------------------------------------------------------
    query = "What is the effect of a contract between the parties?"

    query_embedding = get_embedding(query)

    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_embedding,
        limit=5,
    ).points

    # ---------------------------------------------------------
    # 6. Display results
    # ---------------------------------------------------------
    print("\nSearch results:")

    for result in results:
        print(f"\nScore: {result.score}")
        print(f"Law Number: {result.payload['law_number']}")
        print(f"Title: {result.payload['title']}")
        print(f"Content: {result.payload['content']}")

if __name__ == "__main__":
    main()