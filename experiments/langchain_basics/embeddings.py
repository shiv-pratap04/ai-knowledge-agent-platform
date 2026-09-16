import os

from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings

load_dotenv()
embeddings = GoogleGenerativeAIEmbeddings(
	model="models/text-embedding-004",
	google_api_key=os.environ["GOOGLE_API_KEY"],
)
vector = embeddings.embed_query("The cat sat on the mat.")
print("dimension:", len(vector))
print("first 5:", vector[:5])
