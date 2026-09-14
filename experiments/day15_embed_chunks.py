import sys
import time
from pathlib import Path

from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

UPLOAD_DIR = Path("uploaded_docs")
CHUNK_SIZE = 500
OVERLAP = 50
MODEL_NAME = "all-MiniLM-L6-v2"


def find_pdf():
    if len(sys.argv) > 1:
        return Path(sys.argv[1])

    pdfs = sorted(UPLOAD_DIR.glob("*.pdf"))
    if pdfs:
        return pdfs[0]

    print("Error: no PDF found.")
    print("Upload a PDF via POST /documents, put one in uploaded_docs/, or pass a path:")
    print("  python experiments/day15_embed_chunks.py path/to/file.pdf")
    sys.exit(1)


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    if not text.strip():
        return []
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = end - overlap
    return chunks


def main():
    pdf_path = find_pdf()
    if not pdf_path.exists():
        print(f"Error: file not found: {pdf_path}")
        sys.exit(1)

    print(f"Opening: {pdf_path}")
    reader = PdfReader(str(pdf_path))

    chunks = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        for chunk_index, chunk in enumerate(
            chunk_text(text, chunk_size=CHUNK_SIZE, overlap=OVERLAP)
        ):
            chunks.append(
                {
                    "text": chunk,
                    "page_number": page_number,
                    "chunk_index": chunk_index,
                }
            )

    print(f"Chunks to embed: {len(chunks)}")
    if not chunks:
        print("No text chunks found. Try a PDF with selectable text.")
        sys.exit(1)

    print(f"Loading model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)

    texts = [item["text"] for item in chunks]
    started = time.perf_counter()
    embeddings = model.encode(texts)
    elapsed = time.perf_counter() - started

    records = []
    for item, embedding in zip(chunks, embeddings):
        records.append(
            {
                "text": item["text"],
                "page_number": item["page_number"],
                "chunk_index": item["chunk_index"],
                "embedding": embedding,
            }
        )

    first = records[0]
    preview = first["text"].replace("\n", " ")[:200]

    print(f"Total chunks embedded: {len(records)}")
    print(f"Embedding dimension: {embeddings.shape[1]}")
    print(f"Embedding time: {elapsed:.2f} seconds")
    print()
    print("First chunk sanity check:")
    print(f"  page={first['page_number']} chunk_index={first['chunk_index']}")
    print(f"  text: {preview}")
    print(f"  first 5 values: {first['embedding'][:5]}")


if __name__ == "__main__":
    main()
