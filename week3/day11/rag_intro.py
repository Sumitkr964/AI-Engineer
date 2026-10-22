import os
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
my_api_keys = os.getenv("GROQ_API_KEY")

if not my_api_keys:
    raise ValueError("API key not found!")

client = Groq(api_key = my_api_keys)

model = "openai/gpt-oss-120b"

#step1
knowledge_base={
    "age":25,
    "net worth":20000
}

#step 2 retrieval
def retrieve_info(question):
    question=question.lower()
    if "age" in question:
        return knowledge_base["age"]
    elif "net worth" in question:
        return knowledge_base["net worth"]
    else:
        return None

def ask_llm(question):
    context=retrieve_info(question)
    sys_prompt=f"""answer in one line only. Answer only based on this context . do not hallucinate. context:{context}"""
    system_message={
        "role":"system",
        "content":sys_prompt
    }
    message={
        "role":"user",
        "content":question
    }
    messages=[system_message, message]
    response=client.chat.completions.create(model=model, messages=messages)
    answer=response.choices[0].message.content
    return answer

question="what is pratyush net worth"
print(ask_llm(question))