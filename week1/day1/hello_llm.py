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
role = "user"
prompt = "Do you know padho with pratyush"
# message me role and content
message={
    "role":role,
    "content":prompt
}
messages = [message]
response = client.chat.completions.create(model=model, messages=messages)
# print(response)

print("#######################################")
answer = response.choices[0].message.content
print(answer)