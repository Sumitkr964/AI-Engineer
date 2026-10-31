
import json
from pathlib import Path

from tools import (
    groq,
    MODEL,
    SEARCH_TOOL,
    CALC_TOOL,
    AVAILABLE_TOOLS,
    TokenTracker
)


# ============================================================
# CONFIGURATION
# ============================================================

NOTES_FILE = Path(__file__).parent / "notes.md"

MAX_MANAGER_ROUNDS = 5
MAX_TOOL_ITERATIONS = 5


# ============================================================
# COMMON LLM FUNCTION FOR SPECIALIST AGENTS
# ============================================================

def run_helper_llm(
    task: str,
    tracker: TokenTracker,
    system_prompt: str,
    available_tools: list,
    label: str
) -> str:

    messages = [
        {
            "role": "system",
            "content": system_prompt
        },
        {
            "role": "user",
            "content": task
        }
    ]

    for iteration in range(MAX_TOOL_ITERATIONS):

        response = groq.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=available_tools,
            tool_choice="auto",
            temperature=0
        )

        tracker.add(label, response.usage)

        message = response.choices[0].message

        # Return final response if no more tools are requested
        if not message.tool_calls:
            return message.content or ""

        # Preserve assistant tool-call message
        messages.append(
            message.model_dump(exclude_none=True)
        )

        # Execute requested Python tools
        for tool_call in message.tool_calls:

            tool_name = tool_call.function.name

            arguments = json.loads(
                tool_call.function.arguments
            )

            print(f"[{label}] Executing: {tool_name}")

            if tool_name not in AVAILABLE_TOOLS:
                result = f"Unknown tool: {tool_name}"
            else:
                try:
                    result = AVAILABLE_TOOLS[tool_name](
                        **arguments
                    )
                except Exception as error:
                    result = f"Tool execution failed: {error}"

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": str(result)
            })

    # Ask the agent to provide its answer without more tool calls
    messages.append({
        "role": "user",
        "content": (
            "Tool-call limit reached. "
            "Provide your best final answer using the results already obtained."
        )
    })

    response = groq.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0,
        max_completion_tokens=2048
    )

    tracker.add(label, response.usage)

    return response.choices[0].message.content or ""


# ============================================================
# SEARCH SPECIALIST
# ============================================================

SEARCH_PROMPT = """
You are a web research specialist.

Your responsibilities:

1. Search for facts using the web_search tool.
2. Find the official or most reliable source.
3. Extract exact numerical values.
4. Include source URLs.
5. Do not perform mathematical calculations.

Return a concise, factual research report.
"""


def ask_search_llm(
    task: str,
    tracker: TokenTracker
) -> str:

    print("\n[search_agent] Searching the web...")

    return run_helper_llm(
        task=task,
        tracker=tracker,
        system_prompt=SEARCH_PROMPT,
        available_tools=[SEARCH_TOOL],
        label="search_llm"
    )


# ============================================================
# MATHEMATICS SPECIALIST
# ============================================================

MATHS_PROMPT = """
You are a mathematics specialist.

Your responsibilities:

1. Perform calculations using the calculate tool.
2. Never calculate mentally.
3. Use only the numerical values supplied in the task.
4. Show the formulas and calculation steps.
5. Round percentages and ratios to two decimal places.

You cannot search the internet.

Return the calculation results clearly.
"""


def ask_maths_llm(
    task: str,
    tracker: TokenTracker
) -> str:

    print("\n[maths_agent] Performing calculations...")

    return run_helper_llm(
        task=task,
        tracker=tracker,
        system_prompt=MATHS_PROMPT,
        available_tools=[CALC_TOOL],
        label="maths_llm"
    )


# ============================================================
# HELPER REGISTRY
# ============================================================

HELPERS = {
    "ask_search_llm": ask_search_llm,
    "ask_maths_llm": ask_maths_llm
}


# ============================================================
# MANAGER PROMPT
# ============================================================

MANAGER_PROMPT = """
You are the manager of a multi-agent research system.

You have two specialist agents:

1. ask_search_llm:
   Searches the internet and returns facts with source URLs.

2. ask_maths_llm:
   Performs calculations using a calculator tool.

You cannot search or calculate yourself.

WORKFLOW:

Step 1:
Send a task to ask_search_llm to find the official heights
of the Eiffel Tower and Burj Khalifa.

Step 2:
Read the search agent's results from your notes.

Step 3:
Send the actual numerical heights to ask_maths_llm.

Ask it to calculate:

A. (Eiffel Tower height / Burj Khalifa height) * 100

B. Burj Khalifa height / Eiffel Tower height

Step 4:
Once both results are available, provide the final answer.

The final answer must include:
- Both heights in metres.
- Percentage comparison.
- Number of Eiffel Towers required.
- Source URLs.
- Calculation results to two decimal places.

Do not invent information.

You have a maximum of 5 rounds.
"""


# ============================================================
# MANAGER TOOL DEFINITIONS
# ============================================================

HELPER_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "ask_search_llm",
            "description": (
                "Send a research task to the web search specialist."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "Complete research task."
                    }
                },
                "required": ["task"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ask_maths_llm",
            "description": (
                "Send a calculation task to the mathematics specialist."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "Complete calculation task with numbers."
                    }
                },
                "required": ["task"]
            }
        }
    }
]


# ============================================================
# SAVE AGENT OUTPUT TO NOTES
# ============================================================

def write_note(
    round_no: int,
    helper: str,
    task: str,
    answer: str
):

    with NOTES_FILE.open("a", encoding="utf-8") as file:

        file.write(
            f"## Round {round_no} - {helper}\n\n"
            f"**Task:**\n{task}\n\n"
            f"**Answer:**\n{answer}\n\n"
            f"---\n\n"
        )


# ============================================================
# MANAGER AGENT
# ============================================================

def ask_manager_llm(
    question: str,
    tracker: TokenTracker
) -> str:

    # Reset notes for every new question
    NOTES_FILE.write_text(
        f"# Notes for: {question}\n\n",
        encoding="utf-8"
    )

    def manager_messages():

        notes = NOTES_FILE.read_text(
            encoding="utf-8"
        )

        return [
            {
                "role": "system",
                "content": MANAGER_PROMPT
            },
            {
                "role": "user",
                "content": (
                    f"Original question:\n{question}\n\n"
                    f"Notes collected so far:\n{notes}\n\n"
                    "Decide which specialist to call next. "
                    "If all information is available, "
                    "provide the final answer."
                )
            }
        ]

    # Manager orchestration loop
    for round_no in range(
        1,
        MAX_MANAGER_ROUNDS + 1
    ):

        print(f"\n[manager] Round {round_no}")

        response = groq.chat.completions.create(
            model=MODEL,
            messages=manager_messages(),
            tools=HELPER_TOOLS,
            tool_choice="auto",
            temperature=0
        )

        tracker.add(
            "manager",
            response.usage
        )

        message = response.choices[0].message

        # Manager has finished
        if not message.tool_calls:

            print("\n[manager] Final answer generated.")

            return message.content or ""

        # Execute specialist calls
        for tool_call in message.tool_calls:

            helper_name = tool_call.function.name

            arguments = json.loads(
                tool_call.function.arguments
            )

            task = arguments["task"]

            print(
                f"\n[manager] Calling {helper_name}"
            )

            print(f"[manager] Task: {task}")

            if helper_name not in HELPERS:

                raise ValueError(
                    f"Unknown helper: {helper_name}"
                )

            # Execute specialist
            answer = HELPERS[helper_name](
                task,
                tracker
            )

            # Save specialist result
            write_note(
                round_no,
                helper_name,
                task,
                answer
            )

            print(
                f"\n[manager] {helper_name} completed."
            )

    # ========================================================
    # ROUND LIMIT FALLBACK
    # ========================================================

    print(
        "\n[manager] Maximum rounds reached. "
        "Generating final answer."
    )

    messages = manager_messages()

    messages.append({
        "role": "user",
        "content": (
            "No more specialist calls are allowed. "
            "Generate the final answer using the available notes. "
            "Clearly mention any missing information."
        )
    })

    response = groq.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0
    )

    tracker.add(
        "manager",
        response.usage
    )

    return response.choices[0].message.content or ""


# ============================================================
# STANDALONE TEST
# ============================================================

if __name__ == "__main__":

    tracker = TokenTracker()

    question = input(
        "Ask me anything: "
    )

    answer = ask_manager_llm(
        question,
        tracker
    )

    print("\nFINAL ANSWER:\n")
    print(answer)

    tracker.report("multi agent")
