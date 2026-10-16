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

# structure it
from pydantic import BaseModel 
class Ticket(BaseModel):
    name:str
    email:str
    issue:str

schema=Ticket.model_json_schema()

response_format={
    "type":"json_object"
}

system_prompt=f""""
Extract the personal information from the ticket strictly based on this schema and give a json output.
{schema}
"""
message_system={
    "role": "system",
    "content": system_prompt
}

text = "Hello my name is sumit . I have an Iphone which is not working at all. My address is Delhi. My email is abc@gmail.com. My contact number is 12345"
prompt = f""""
This is a customer ticket. Please extract the personal information from this.
{text}
"""

# message me role and content 
message={
    "role": role,
    "content": prompt
}
messages = [message_system, message]
response = client.chat.completions.create(model=model, messages=messages, response_format=response_format)
# print(response)

# print("#######################################")
answer = response.choices[0].message.content
print(answer)

# isko padhte kaise hai 
import json
raw_json=answer
data_file=json.loads(raw_json)
ticket=Ticket(**data_file)
print(ticket.name)
print(ticket.email)
print(ticket.issue)