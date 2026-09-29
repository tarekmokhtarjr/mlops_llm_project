from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from pydantic import BaseModel, Field
from typing import Optional
import os

load_dotenv()


class GuardResult(BaseModel):
    safety: str = Field(description="Safe, Unsafe, or Controversial")
    categories: str = Field(description="Detected safety categories")
    refusal: Optional[str] = Field(
        default=None, description="Yes or No, only for response moderation"
    )


class GuardModel:
    def __init__(self):
        """
        Initializes the GuardModel with configurations from environment variables.
        """
        self.guard_model = ChatOpenAI(
            base_url=os.getenv("GUARD_MODEL_SERVER")
            + ":"
            + os.getenv("GUARD_PORT_HOST"),
            api_key=os.getenv("GUARD_MODEL_API_KEY"),
            model=os.getenv("GUARD_MODEL"),
            temperature=0,
            max_tokens=128,
        )
        self.structured_guard = self.guard_model.with_structured_output(
            GuardResult
        )

    def check_input(self, query: str) -> GuardResult:
        """
        Checks the safety of the input query using the guard model.

        Args:
            query (str): The input query to be checked.

        Returns:
            GuardResult: A GuardResult object containing the safety assessment.
        """
        return self.structured_guard.invoke([HumanMessage(content=query)])

    def check_output(self, query: str, answer: str) -> GuardResult:
        """
        Checks the safety of the output answer relative to the input query using the guard model.

        Args:
            query (str): The input query.
            answer (str): The output answer to be checked.

        Returns:
            GuardResult: A GuardResult object containing the safety assessment.
        """
        return self.structured_guard.invoke(
            [HumanMessage(content=query), AIMessage(content=answer)]
        )
