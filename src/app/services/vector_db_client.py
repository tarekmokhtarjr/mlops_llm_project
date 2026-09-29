from typing import Any, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
)


class VectorDBClientWrapper:
    """
    Application-level wrapper around the official Qdrant client.

    Responsible for:
    - connecting to Qdrant
    - collection management
    - inserting vectors
    - vector similarity search
    - retrieving stored points

    Does NOT handle:
    - embedding generation
    - LLM calls
    - prompt construction
    - RAG orchestration
    """

    def __init__(
        self,
        url: str,
        collection_name: str,
        api_key: Optional[str] = None,
    ) -> None:
        """
        Initialize the VectorDBClientWrapper.

        Args:
            url (str): The URL of the Qdrant server.
            collection_name (str): The name of the collection to interact with.
            api_key (Optional[str], optional): The API key for authentication. Defaults to None.
        """
        self.collection_name = collection_name

        self.client = QdrantClient(
            url=url,
            api_key=api_key,
        )

    def collection_exists(self) -> bool:
        """
        Check whether the configured collection exists.

        Returns:
            bool: True if the collection exists, False otherwise.
        """
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
        """
        Create the configured collection.

        Args:
            vector_size (int): The size of the vectors in the collection.
            distance (Distance, optional): The distance metric to use for similarity search. Defaults to Distance.COSINE.
        """
        if self.collection_exists():
            return

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
        """
        Insert or update vectors and their payloads.

        Args:
            points (List[PointStruct]): The list of points to upsert.
        """
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
        Search for vectors similar to the query vector.

        Args:
            query_vector (List[float]): The query vector to search against.
            limit (int, optional): The maximum number of results to return. Defaults to 5.
            score_threshold (Optional[float], optional): The minimum score threshold for results. Defaults to None.
            query_filter (Optional[Any], optional): A filter to apply to the search. Defaults to None.

        Returns:
            List[PointStruct]: A list of points similar to the query vector.
        """
        return self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=limit,
            score_threshold=score_threshold,
            query_filter=query_filter,
        ).points

    def get_by_id(self, point_id: Any) -> Optional[PointStruct]:
        """
        Retrieve a point by its ID.

        Args:
            point_id (Any): The ID of the point to retrieve.

        Returns:
            Optional[PointStruct]: The point with the specified ID, or None if not found.
        """
        # TODO: Remove if redundant
        result = self.client.retrieve(
            collection_name=self.collection_name,
            ids=[point_id],
        )

        return result[0] if result else None

    def delete(self, point_ids: List[Any]) -> None:
        """
        Delete points from the collection.

        Args:
            point_ids (List[Any]): The list of IDs of the points to delete.
        """
        # TODO: Remove if redundant
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=point_ids,
        )
