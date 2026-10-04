from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from pydantic import BaseModel, Field
from typing import Optional
import os
import re

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

    def _parse_response(self, content: str) -> dict:
        """
        Parses the response content to extract safety, categories, and refusal information.

        Args:
            content (str): The raw response content from which to extract information.

        Returns:
            dict: A dictionary containing the parsed information with the following keys:
                - 'safety' (str): The safety status ('Safe', 'Unsafe', 'Controversial', or 'Unknown').
                - 'categories' (str): The categories associated with the response ('Unknown' if not found).
                - 'refusal' (str): The refusal status ('Yes' or 'No', or None if not found).
                - 'is_safe' (bool): A boolean indicating whether the response is safe (True if 'safety' is 'Safe', False otherwise).
                - 'raw' (str): The original raw response content.

        Example:
            >>> response_content = "Safety: Safe\\nCategories: Politics\\nRefusal: No"
            >>> _parse_response(response_content)
            {
                'safety': 'Safe',
                'categories': 'Politics',
                'refusal': 'No',
                'is_safe': True,
                'raw': 'Safety: Safe\\nCategories: Politics\\nRefusal: No'
            }
        """
        safety_match = re.search(
            r"Safety:\s*(Safe|Unsafe|Controversial)",
            content,
            re.IGNORECASE
        )
        categories_match = re.search(
            r"Categories:\s*(.+)",
            content,
            re.IGNORECASE
        )
        refusal_match = re.search(
            r"Refusal:\s*(Yes|No)",
            content,
            re.IGNORECASE
        )
        safety = (
            safety_match.group(1)
            if safety_match
            else "Unknown"
        )
        categories = (
            categories_match.group(1).strip()
            if categories_match
            else "Unknown"
        )
        refusal = (
            refusal_match.group(1)
            if refusal_match
            else None
        )
        return {
            "safety": safety,
            "categories": categories,
            "refusal": refusal,
            "is_safe": safety.lower() == "safe",
            "raw": content,
        }
