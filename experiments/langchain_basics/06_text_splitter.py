from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

docs = PyPDFLoader(str(Path("uploaded_docs/CDAC Report.pdf"))).load()
chunks = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50).split_documents(docs)
print("chunks:", len(chunks))
print("first chunk:", chunks[0].page_content[:200].replace("\n", " "))
