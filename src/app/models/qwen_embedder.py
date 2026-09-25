from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
import os

load_dotenv()

class embeddingModel:

    def __init__(self):
        self.embedding_model = OpenAIEmbeddings(
            base_url=os.getenv("EMBEDDING_MODEL_SERVER"),
            api_key=os.getenv("EMBEDDING_MODEL_API_KEY"),
            model=os.getenv("EMBEDDING_MODEL"),
        )

    def embedd(self, query: str) -> list:
        response = self.embedding_model.embed_query(query)
        print(type(response))
        return response
