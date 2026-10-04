from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
import os

load_dotenv()


class ChatBotLlmModel:
    """
    Represents a chatbot using OpenAI's ChatOpenAI model.
    """

    def __init__(self):
        """
        Initializes the ChatBot with configurations from environment variables.
        """
        self.chatbot_llm = ChatOpenAI(
            base_url=os.getenv("CHATBOT_SERVER")
            + ":"
            + os.getenv("CHATBOT_SERVER_PORT"),
            api_key=os.getenv("CHATBOT_API_KEY"),
            model=os.getenv("CHATBOT_MODEL"),
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
