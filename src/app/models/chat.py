from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
import os

load_dotenv()


class ChatBotLlmModel:
    """
    Represents a chatbot using OpenAI's ChatOpenAI model.
    """

    def __init__(self):
        self.model_name = os.getenv(
            "CHATBOT_MODEL",
            "Qwen/Qwen2.5-0.5B-Instruct",
        )
        self.server = os.getenv(
            "CHATBOT_SERVER",
            "http://localhost",
        )
        self.server_port = os.getenv(
            "CHATBOT_SERVER_PORT",
            "8000",
        )
        self.api_key = os.getenv(
            "CHATBOT_API_KEY",
            "dumb",
        )
        self.base_url = (
            f"{self.server}:{self.server_port}/v1"
        )
        self.chatbot_llm = ChatOpenAI(
            model=self.model_name,
            base_url=self.base_url,
            api_key=self.api_key,
            temperature=0,
        )

    def invoke(self, prompt: str) -> str:
        """
        Invokes the model with the given prompt and returns the response content.

        Args:
            prompt (str): The input prompt for the model.

        Returns:
            str: The content of the model's response.
        """
        response = self.chatbot_llm.invoke(prompt)
        return response.content
