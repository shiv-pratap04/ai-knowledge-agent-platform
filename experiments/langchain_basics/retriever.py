from langchain_core.vectorstores import InMemoryVectorStore
from langchain_huggingface import HuggingFaceEmbeddings

embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
texts = [
    "The cat sat on the mat.",
    "A feline rested on the rug.",
    "The stock market crashed today.",
    "Investors panicked as prices fell.",
]
retriever = InMemoryVectorStore.from_texts(texts, embeddings).as_retriever(search_kwargs={"k": 2})
for doc in retriever.invoke("My kitten is sleeping on the couch."):
    print(doc.page_content)
