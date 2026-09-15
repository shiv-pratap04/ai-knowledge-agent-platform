from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader

pdf = Path("uploaded_docs/CDAC Report.pdf")
docs = PyPDFLoader(str(pdf)).load()
print("documents (pages):", len(docs))
print("first page preview:", docs[0].page_content[:200].replace("\n", " "))
