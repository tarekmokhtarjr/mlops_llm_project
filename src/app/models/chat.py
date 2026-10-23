from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
import os


load_dotenv()


class ChatBotLlmModel:
    """
    Chatbot LLM backed by the OpenAI-compatible
    vLLM server running in the llm container.
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
        Generate an answer from the LLM.

        Args:
            prompt: Prompt sent to the chatbot model.

        Returns:
            Generated answer as a string.
        """

        response = self.chatbot_llm.invoke(
            prompt
        )

        return str(response.content)