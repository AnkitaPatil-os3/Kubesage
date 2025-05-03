from openai import OpenAI
from openai import OpenAI, OpenAIError
from pydantic import ValidationError
from dotenv import load_dotenv
import os
from app.models import Incident, Plan, Action
# print(os.environ("PATH"))
# Load environment variables from .env file
load_dotenv(override=True)
# Initialize the OpenAI client with OpenRouter base URL and your API key
# Ensure the base URL has the correct protocol
base_url = os.getenv("OPENAI_BASE_URL")
if base_url and not base_url.startswith(("http://", "https://")):
    base_url = "https://" + base_url

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=base_url  # OpenRouter's OpenAI-compatible endpoint
)

# Use any model available on OpenRouter (e.g., mistralai/mistral-7b-instruct)
response = client.chat.completions.create(
    model=os.getenv("OPENAI_MODEL", "gpt-4-turbo"),  # Use OpenRouter's model ID
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Explain how gravity works."}
    ]
)

# Print the assistant's reply
print(response.choices[0].message.content)
