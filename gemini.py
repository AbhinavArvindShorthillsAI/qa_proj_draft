from langchain_google_genai import ChatGoogleGenerativeAI
import os
from dotenv import load_dotenv
load_dotenv()

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",  # or "gemini-1.5-pro"
    temperature=0.7,
    google_api_key=os.getenv("API_KEY"),  # Ensure you have set this in your .env file
)
response= llm.invoke("Hello how are you doing")
print(response.content)