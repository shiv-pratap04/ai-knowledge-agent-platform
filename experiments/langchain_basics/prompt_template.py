from langchain_core.prompts import PromptTemplate
from langchain_ollama import ChatOllama

llm = ChatOllama(model="llama3.2")
prompt = PromptTemplate.from_template("Explain {topic} in one sentence.")
message = prompt.format(topic="vector embeddings")
print(llm.invoke(message).content)
