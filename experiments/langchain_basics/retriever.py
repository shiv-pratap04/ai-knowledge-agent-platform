import os

from dotenv import load_dotenv
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_google_genai import GoogleGenerativeAIEmbeddings

load_dotenv()
embeddings = GoogleGenerativeAIEmbeddings(
    model="models/text-embedding-004",
    google_api_key=os.environ["GOOGLE_API_KEY"],
)
texts = [
    "The cat sat on the mat.",
    "A feline rested on the rug.",
    "The stock market crashed today.",
    "Investors panicked as prices fell.",
]
retriever = InMemoryVectorStore.from_texts(texts, embeddings).as_retriever(search_kwargs={"k": 2})
for doc in retriever.invoke("My kitten is sleeping on the couch."):
    print(doc.page_content)
