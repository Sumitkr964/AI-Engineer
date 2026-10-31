
import os
import math

from dotenv import load_dotenv
from groq import Groq
from tavily import TavilyClient


# ============================================================
# SETUP
# ============================================================

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is missing from your .env file")

if not TAVILY_API_KEY:
    raise ValueError("TAVILY_API_KEY is missing from your .env file")

groq = Groq(
    api_key=GROQ_API_KEY,
    max_retries=10
)

tavily = TavilyClient(
    api_key=TAVILY_API_KEY
)

MODEL = "openai/gpt-oss-120b"


# ============================================================
# TOOL 1: WEB SEARCH
# ============================================================

def web_search(query: str) -> str:
    """
    Search the web using Tavily.
    Returns titles, URLs and relevant content.
    """

    try:
        response = tavily.search(
            query=query,
            max_results=2,
            search_depth="basic"
        )

        results = []

        for result in response.get("results", []):

            results.append(
                f"Title: {result.get('title', 'N/A')}\n"
                f"URL: {result.get('url', 'N/A')}\n"
                f"Content: {result.get('content', '')[:400]}"
            )

        if not results:
            return "No search results found."

        return "\n\n".join(results)

    except Exception as e:
        return f"Search failed: {str(e)}"


# ============================================================
# TOOL 2: PYTHON CALCULATOR
# ============================================================

SAFE_MATH = {
    name: getattr(math, name)
    for name in dir(math)
    if not name.startswith("_")
}

SAFE_MATH.update({
    "abs": abs,
    "round": round,
    "min": min,
    "max": max
})


def calculate(expression: str) -> str:
    """
    Evaluate a mathematical expression.
    Supports arithmetic and standard math functions.
    """

    try:
        result = eval(
            expression,
            {"__builtins__": {}},
            SAFE_MATH
        )

        if not isinstance(result, (int, float)):
            return "Invalid mathematical expression."

        if not math.isfinite(result):
            return "Result is not finite."

        return str(result)

    except Exception as e:
        return f"Calculation failed: {str(e)}"


# ============================================================
# TOOL DEFINITIONS FOR GROQ
# ============================================================

SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": (
            "Search the web for current information, facts, "
            "statistics and reliable source URLs."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "A specific web search query."
                }
            },
            "required": ["query"]
        }
    }
}


CALC_TOOL = {
    "type": "function",
    "function": {
        "name": "calculate",
        "description": (
            "Evaluate a mathematical expression using Python. "
            "Supports arithmetic and math functions."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Example: (330 / 828) * 100"
                }
            },
            "required": ["expression"]
        }
    }
}


# ============================================================
# TOOL EXECUTION MAPPING
# ============================================================

AVAILABLE_TOOLS = {
    "web_search": web_search,
    "calculate": calculate
}


# ============================================================
# TOKEN TRACKER
# ============================================================

class TokenTracker:
    """
    Tracks token usage across all LLM calls.
    Usage is grouped by agent name.
    """

    def __init__(self):

        self.by_label = {}

    def add(self, label: str, usage):

        if usage is None:
            return

        entry = self.by_label.setdefault(
            label,
            {
                "calls": 0,
                "prompt": 0,
                "completion": 0,
                "total": 0
            }
        )

        entry["calls"] += 1

        entry["prompt"] += usage.prompt_tokens

        entry["completion"] += usage.completion_tokens

        entry["total"] += usage.total_tokens

    @property
    def total(self) -> int:

        return sum(
            entry["total"]
            for entry in self.by_label.values()
        )

    @property
    def calls(self) -> int:

        return sum(
            entry["calls"]
            for entry in self.by_label.values()
        )

    def report(self, title: str):

        print(f"\n--- Token usage: {title} ---")

        print(
            f"{'LLM':<14}"
            f"{'calls':>6}"
            f"{'prompt':>10}"
            f"{'completion':>12}"
            f"{'total':>10}"
        )

        for label, entry in self.by_label.items():

            print(
                f"{label:<14}"
                f"{entry['calls']:>6}"
                f"{entry['prompt']:>10}"
                f"{entry['completion']:>12}"
                f"{entry['total']:>10}"
            )

        print(
            f"{'TOTAL':<14}"
            f"{self.calls:>6}"
            f"{'':>10}"
            f"{'':>12}"
            f"{self.total:>10}"
        )
