from langchain_ollama import ChatOllama

llm = ChatOllama(model="llama3.2")
response = llm.invoke("Explain what RAG means in one sentence.")
print(response.content)
