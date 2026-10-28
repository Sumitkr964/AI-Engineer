import os
import json
import ast
import operator
from dotenv import load_dotenv
from groq import Groq
from tavily import TavilyClient


# --------------------------------------------------
# 1. Load API keys and initialize clients
# --------------------------------------------------

load_dotenv()

groq = Groq(api_key=os.getenv("GROQ_API_KEY"))
tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

MODEL = "openai/gpt-oss-120b"


# --------------------------------------------------
# 2. Tool 1: Web search using Tavily
# --------------------------------------------------

def web_search(query: str) -> str:
    """Search the web and return relevant results."""

    try:
        response = tavily.search(
            query=query,
            max_results=5
        )

        results = response.get("results", [])

        if not results:
            return "No relevant web search results found."

        formatted_results = []

        for result in results:
            formatted_results.append(
                f"Title: {result.get('title', 'N/A')}\n"
                f"URL: {result.get('url', 'N/A')}\n"
                f"Content: {result.get('content', 'N/A')}"
            )

        return "\n\n".join(formatted_results)

    except Exception as e:
        return f"Web search failed: {str(e)}"


# --------------------------------------------------
# 3. Tool 2: Safe math calculator
# --------------------------------------------------

def calculate(expression: str) -> str:
    """Evaluate basic arithmetic without using eval()."""

    operations = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.UAdd: operator.pos,
        ast.USub: operator.neg,
    }

    def evaluate(node):
        if isinstance(node, ast.Constant):
            if type(node.value) in (int, float):
                return node.value
            raise ValueError("Only numeric values are allowed.")

        if isinstance(node, ast.BinOp):
            op_type = type(node.op)

            if op_type not in operations:
                raise ValueError("Unsupported operator.")

            left = evaluate(node.left)
            right = evaluate(node.right)

            # Prevent excessively large exponent calculations.
            if op_type is ast.Pow:
                if abs(right) > 1000:
                    raise ValueError("Exponent is too large.")

            result = operations[op_type](left, right)

            if isinstance(result, (int, float)):
                if abs(result) == float("inf"):
                    raise ValueError("Result is too large.")
                if isinstance(result, float) and result != result:
                    raise ValueError("Invalid numeric result.")

            return result

        if isinstance(node, ast.UnaryOp):
            op_type = type(node.op)

            if op_type not in operations:
                raise ValueError("Unsupported unary operator.")

            return operations[op_type](evaluate(node.operand))

        raise ValueError("Invalid mathematical expression.")

    try:
        if not isinstance(expression, str):
            return "Error: expression must be a string."

        if len(expression) > 200:
            return "Error: expression is too long."

        tree = ast.parse(expression, mode="eval")
        result = evaluate(tree.body)

        return str(result)

    except Exception as e:
        return f"Calculation error: {str(e)}"


# --------------------------------------------------
# 4. Define both tools in Groq's standard format
# --------------------------------------------------

tools = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Search the internet using Tavily for current facts, "
                "news, schedules, events, and other information that "
                "requires web research. The query must be a string."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The question or topic to search for."
                    }
                },
                "required": ["query"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": (
                "Calculate a mathematical expression using basic "
                "arithmetic. Use this tool for calculations instead "
                "of calculating mentally. Supports +, -, *, /, //, "
                "%, **, parentheses, and unary signs."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": (
                            "A mathematical expression, such as "
                            "'2 * 2' or '(10 + 5) / 3'."
                        )
                    }
                },
                "required": ["expression"],
                "additionalProperties": False
            }
        }
    }
]


# --------------------------------------------------
# 5. Map tool names to Python functions
# --------------------------------------------------

available_functions = {
    "web_search": web_search,
    "calculate": calculate,
}


# --------------------------------------------------
# 6. Run the AI agent
# --------------------------------------------------

def run_agent(query: str) -> str:
    """Run the agent and return its final answer as a string."""

    messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful AI agent with two tools: web_search "
                "and calculate. Decide which tool is appropriate for "
                "the user's question. Use web_search for information "
                "requiring research and calculate for arithmetic. "
                "You may use multiple tools or multiple rounds when "
                "necessary. Use tool results to answer accurately. "
                "If no tool is needed, answer directly. "
                "Return a clear final answer to the user."
            )
        },
        {
            "role": "user",
            "content": query
        }
    ]

    # Allow multiple rounds of tool calls.
    max_iterations = 8

    for iteration in range(max_iterations):
        response = groq.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )

        message = response.choices[0].message

        # Add the assistant message before processing its tool calls.
        messages.append(message.model_dump(exclude_none=True))

        # No tool calls means the model has produced its final answer.
        if not message.tool_calls:
            return message.content or "The model returned an empty answer."

        # Execute every requested tool call.
        for tool_call in message.tool_calls:
            function_name = tool_call.function.name

            try:
                arguments = json.loads(
                    tool_call.function.arguments
                )

                function = available_functions.get(function_name)

                if function is None:
                    result = f"Error: unknown tool '{function_name}'."

                elif function_name == "web_search":
                    query_arg = arguments.get("query")

                    if not isinstance(query_arg, str) or not query_arg.strip():
                        result = "Error: a non-empty query string is required."
                    else:
                        result = function(query_arg)

                elif function_name == "calculate":
                    expression = arguments.get("expression")

                    if not isinstance(expression, str):
                        result = "Error: expression must be a string."
                    else:
                        result = function(expression)

                else:
                    result = "Error: unsupported tool."

            except Exception as e:
                result = f"Tool execution failed: {str(e)}"

            # Return the tool result to the model.
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": str(result)
            })

    # If the model keeps requesting tools, make one final
    # request without tools so it must produce a final answer.
    final_response = groq.chat.completions.create(
        model=MODEL,
        messages=messages,
        tool_choice="none"
    )

    return (
        final_response.choices[0].message.content
        or "Unable to generate a final answer."
    )


# --------------------------------------------------
# 7. Run the program
# --------------------------------------------------

if __name__ == "__main__":
    while True:
        query = input("\nAsk something (or type 'exit'): ").strip()

        if query.lower() in ("exit", "quit"):
            print("Goodbye!")
            break

        if not query:
            print("Please enter a question.")
            continue

        try:
            answer = run_agent(query)
            print("\nAI Agent:")
            print(answer)

        except Exception as e:
            print(f"\nAgent error: {e}")




# import ast
# import json
# import operator as op
# import os

# from dotenv import load_dotenv
# from groq import Groq
# from tavily import TavilyClient

# load_dotenv()

# groq = Groq(api_key=os.getenv("GROQ_API_KEY"))
# tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

# MODEL = "openai/gpt-oss-120b"

# # --- Tool implementations -----------------------------------------------

# def web_search(query: str) -> str:
#     result = tavily.search(query=query)
#     results = result.get("results", [])
#     if not results:
#         return "No results found."
#     lines = [f"{r['title']}: {r['content']} ({r['url']})" for r in results]
#     return "\n".join(lines)


# _ALLOWED_OPS = {
#     ast.Add: op.add,
#     ast.Sub: op.sub,
#     ast.Mult: op.mul,
#     ast.Div: op.truediv,
#     ast.Pow: op.pow,
#     ast.Mod: op.mod,
#     ast.FloorDiv: op.floordiv,
#     ast.USub: op.neg,
#     ast.UAdd: op.pos,
# }


# def _eval_node(node):
#     if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
#         return node.value
#     if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_OPS:
#         return _ALLOWED_OPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
#     if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_OPS:
#         return _ALLOWED_OPS[type(node.op)](_eval_node(node.operand))
#     raise ValueError("Unsupported expression")


# def calculate(expression: str) -> str:
#     try:
#         tree = ast.parse(expression, mode="eval")
#         return str(_eval_node(tree.body))
#     except Exception as exc:
#         return f"Error evaluating expression: {exc}"


# # --- Tool schema for the LLM ---------------------------------------------

# tools = [
#     {
#         "type": "function",
#         "function": {
#             "name": "web_search",
#             "description": "Search the web for up-to-date information and return a summary of results.",
#             "parameters": {
#                 "type": "object",
#                 "properties": {
#                     "query": {
#                         "type": "string",
#                         "description": "The search query to look up on the web.",
#                     }
#                 },
#                 "required": ["query"],
#             },
#         },
#     },
#     {
#         "type": "function",
#         "function": {
#             "name": "calculate",
#             "description": "Evaluate a basic math expression (addition, subtraction, multiplication, division, exponents) and return the result.",
#             "parameters": {
#                 "type": "object",
#                 "properties": {
#                     "expression": {
#                         "type": "string",
#                         "description": "A math expression to evaluate, e.g. '2*2' or '(3+5)/4'.",
#                     }
#                 },
#                 "required": ["expression"],
#             },
#         },
#     },
# ]

# available_functions = {
#     "web_search": web_search,
#     "calculate": calculate,
# }


# # --- Agent loop ------------------------------------------------------------

# def run_agent(user_query: str) -> str:
#     messages = [{"role": "user", "content": user_query}]

#     response = groq.chat.completions.create(
#         model=MODEL,
#         messages=messages,
#         tools=tools,
#         tool_choice="auto",
#     )

#     response_message = response.choices[0].message
#     tool_calls = response_message.tool_calls

#     if not tool_calls:
#         return response_message.content

#     messages.append(response_message)

#     for tool_call in tool_calls:
#         function_name = tool_call.function.name
#         function_to_call = available_functions[function_name]
#         function_args = json.loads(tool_call.function.arguments)

#         function_response = function_to_call(**function_args)

#         messages.append(
#             {
#                 "role": "tool",
#                 "tool_call_id": tool_call.id,
#                 "name": function_name,
#                 "content": function_response,
#             }
#         )

#     second_response = groq.chat.completions.create(
#         model=MODEL,
#         messages=messages,
#     )

#     return second_response.choices[0].message.content


# if __name__ == "__main__":
#     query = input("Ask something: ")
#     answer = run_agent(query)
#     print(answer)