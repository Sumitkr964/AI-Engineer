
import os
from groq import Groq
from tavily import TavilyClient


def ask_llm(query, tracker):

    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

    # Step 1: Search the web
    search_results = tavily.search(
        query=query,
        max_results=5
    )

    context = "\n".join(
        [
            f"Title: {result['title']}\n"
            f"Content: {result['content']}\n"
            f"URL: {result['url']}"
            for result in search_results["results"]
        ]
    )

    # Step 2: Ask Groq
    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a research assistant. "
                    "Answer using the provided search results. "
                    "Show calculations clearly and cite source URLs."
                )
            },
            {
                "role": "user",
                "content": f"Question: {query}\n\nSearch results:\n{context}"
            }
        ],
        temperature=0
    )

    # Step 3: Extract answer
    answer = response.choices[0].message.content

    # Step 4: Track token usage
    usage = response.usage

    if usage:
        tracker.add("single_agent", usage)

    # Step 5: Return answer
    return answer
