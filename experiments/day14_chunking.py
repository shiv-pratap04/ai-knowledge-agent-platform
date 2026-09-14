import sys
from pathlib import Path

from pypdf import PdfReader

UPLOAD_DIR = Path("uploaded_docs")
CHUNK_SIZE = 500
OVERLAP = 50


def find_pdf():
    if len(sys.argv) > 1:
        return Path(sys.argv[1])

    pdfs = sorted(UPLOAD_DIR.glob("*.pdf"))
    if pdfs:
        return pdfs[0]

    print("Error: no PDF found.")
    print("Upload a PDF via POST /documents, put one in uploaded_docs/, or pass a path:")
    print("  python experiments/day14_chunking.py path/to/file.pdf")
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


def print_chunks(items):
    for item in items:
        preview = item["text"].replace("\n", " ")
        print(
            f"page={item['page_number']} chunk_index={item['chunk_index']} "
            f"char_count={item['char_count']}"
        )
        print(f"  start: {preview[:80]}")
        print(f"  end:   {preview[-80:]}")
        print()


def first_overlapping_group(all_chunks):
    by_page = {}
    for item in all_chunks:
        by_page.setdefault(item["page_number"], []).append(item)
    for page_number in sorted(by_page):
        group = by_page[page_number]
        if len(group) >= 2:
            return group
    return []


def main():
    pdf_path = find_pdf()
    if not pdf_path.exists():
        print(f"Error: file not found: {pdf_path}")
        sys.exit(1)

    print(f"Opening: {pdf_path}")
    print(f"chunk_size={CHUNK_SIZE}, overlap={OVERLAP}\n")

    reader = PdfReader(str(pdf_path))
    all_chunks = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        page_chunks = chunk_text(text, chunk_size=CHUNK_SIZE, overlap=OVERLAP)
        for chunk_index, chunk in enumerate(page_chunks):
            all_chunks.append(
                {
                    "text": chunk,
                    "page_number": page_number,
                    "chunk_index": chunk_index,
                    "char_count": len(chunk),
                }
            )

    print(f"Total chunks: {len(all_chunks)}\n")
    print("First 3 chunks:\n")
    print_chunks(all_chunks[:3])

    overlapping = first_overlapping_group(all_chunks)
    if overlapping:
        print(
            f"First page with overlapping chunks (page {overlapping[0]['page_number']}):\n"
        )
        print_chunks(overlapping[:3])
        first_end = overlapping[0]["text"][-OVERLAP:]
        second_start = overlapping[1]["text"][:OVERLAP]
        print("Overlap check (end of chunk 0 vs start of chunk 1):")
        print(f"  match: {first_end == second_start}")
        print(f"  overlap text: {first_end.replace(chr(10), ' ')}")
    else:
        print("No page produced more than one chunk, so overlap cannot be shown.")


if __name__ == "__main__":
    main()
