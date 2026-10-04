from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
import os

load_dotenv()


class EmbeddingModel:
    """
    Represents a model for generating embeddings using OpenAI's OpenAIEmbeddings.
    """

    def __init__(self):
        """
        Initializes the EmbeddingModel with configurations from environment variables.
        """
        self.embedding_model = OpenAIEmbeddings(
            base_url=os.getenv("EMBEDDING_MODEL_SERVER")
            + ":"
            + os.getenv("EMBEDDING_MODEL_SERVER_PORT"),
            api_key=os.getenv("EMBEDDING_MODEL_API_KEY"),
            model=os.getenv("EMBEDDING_MODEL"),
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
