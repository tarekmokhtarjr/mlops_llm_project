from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
import os

load_dotenv()
class chatBot:
    def __init__(self):
        self.chatbot_llm = ChatOpenAI(
            base_url=os.getenv("CHATBOT_SERVER"),
            api_key=os.getenv("CHATBOT_API_KEY"),
            model=os.getenv("CHATBOT_MODEL"),
        )
