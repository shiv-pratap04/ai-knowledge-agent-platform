from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_ollama import ChatOllama

prompt = PromptTemplate.from_template("Explain {topic} in one sentence.")
chain = prompt | ChatOllama(model="llama3.2") | StrOutputParser()
print(chain.invoke({"topic": "retrieval augmented generation"}))
