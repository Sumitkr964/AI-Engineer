Restaurant order management agent built with LangGraph.

Flow:
    user_input -> llm -> order_confirm -> llm -> cook -> llm -> serve -> llm -> END

The `llm` node is the "brain": every other node reports back to it by writing
`status`, and the llm reads the state (status + retry counters) to decide what
to say to the user and which node runs next.

uv add langgraph langchain-groq python-dotenv