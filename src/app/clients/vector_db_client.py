from typing import Any, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)


class VectorDBClientWrapper:
    def __init__(
        self,
        url: str,
        collection_name: str,
        api_key: Optional[str] = None,
    ) -> None:
        self.collection_name = collection_name

        self.client = QdrantClient(
            url=url,
            api_key=api_key,
        )

    def collection_exists(self) -> bool:
        collections = self.client.get_collections()

        return any(
            collection.name == self.collection_name
            for collection in collections.collections
        )

    def create_collection(
        self,
        vector_size: int,
        distance: Distance = Distance.COSINE,
    ) -> None:
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=vector_size,
                distance=distance,
            ),
        )

    def upsert(
        self,
        points: List[PointStruct],
    ) -> None:
        self.client.upsert(
            collection_name=self.collection_name,
            points=points,
        )

    def search(
        self,
        query_vector: List[float],
        limit: int = 5,
        score_threshold: Optional[float] = None,
        query_filter: Optional[Any] = None,
    ) -> List[PointStruct]:
        """
        Semantic/vector search.
        """

        response = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=limit,
            score_threshold=score_threshold,
            query_filter=query_filter,
            with_payload=True,
        )

        return response.points

    def search_article(
        self,
        law_number: str,
    ) -> List[PointStruct]:
        """
        Exact article lookup.

        Example:

            law_number = "مادة ١"
        """

        results, _ = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="law_number",
                        match=MatchValue(
                            value=law_number,
                        ),
                    )
                ]
            ),
            limit=1,
            with_payload=True,
            with_vectors=False,
        )

        return results

    def get_all_documents(
        self,
    ) -> List[PointStruct]:
        """
        Retrieve all indexed documents.

        Used for lexical retrieval.

        This is intentionally kept separate from semantic
        search because lexical retrieval works directly
        against the article text.
        """

        all_points = []

        offset = None

        while True:

            points, next_offset = self.client.scroll(
                collection_name=self.collection_name,
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )

            all_points.extend(points)

            if next_offset is None:
                break

            offset = next_offset

        return all_points
