from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
import os

load_dotenv()


class EmbeddingModel:
    """
    Represents a model for generating embeddings using OpenAI's OpenAIEmbeddings.
    """

    def __init__(self):
        self.model_name = os.getenv(
            "EMBEDDING_MODEL",
            "Qwen/Qwen3-Embedding-0.6B",
        )

        self.server = os.getenv(
            "EMBEDDING_MODEL_SERVER",
            "http://localhost",
        )

        self.server_port = os.getenv(
            "EMBEDDING_MODEL_SERVER_PORT",
            "8000",
        )

        self.api_key = os.getenv(
            "EMBEDDING_MODEL_API_KEY",
            "dumb",
        )

        self.base_url=(
            os.getenv("EMBEDDING_MODEL_SERVER")
            + ":"
            + os.getenv("EMBEDDING_MODEL_SERVER_PORT")
            + "/v1"
        )

        self.embedding_model = OpenAIEmbeddings(
            base_url=self.base_url,
            api_key=self.api_key,
            model=self.model_name,
        )

    def embed(self, query: str) -> list:
        """
        Generates embeddings for the given query.

        Args:
            query (str): The input query to generate embeddings for.

        Returns:
            list: A list containing the embeddings.
        """
        response = self.embedding_model.embed_query(query)
        return response
