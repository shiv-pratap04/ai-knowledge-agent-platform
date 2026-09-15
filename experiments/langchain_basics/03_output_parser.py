from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_ollama import ChatOllama

llm = ChatOllama(model="llama3.2")
raw = (llm | StrOutputParser()).invoke(
    'Return JSON only, no markdown: {"summary": "one sentence about RAG"}'
)
print("raw string:", raw)
print("parsed:", JsonOutputParser().parse(raw))
