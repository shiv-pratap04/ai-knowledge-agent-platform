CHUNK_SIZE = 500
OVERLAP = 50


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = OVERLAP) -> list[str]:
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


def chunk_pages(pages: list[dict]) -> list[dict]:
    chunks = []
    for page in pages:
        page_chunks = chunk_text(page["text"])
        for chunk_index, text in enumerate(page_chunks):
            chunks.append(
                {
                    "text": text,
                    "page_number": page["page_number"],
                    "chunk_index": chunk_index,
                }
            )
    return chunks
