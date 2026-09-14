import sys
from pathlib import Path

from pypdf import PdfReader

UPLOAD_DIR = Path("uploaded_docs")
EMPTY_PAGE_THRESHOLD = 20


def find_pdf():
    if len(sys.argv) > 1:
        return Path(sys.argv[1])

    pdfs = sorted(UPLOAD_DIR.glob("*.pdf"))
    if pdfs:
        return pdfs[0]

    print("Error: no PDF found.")
    print("Upload a PDF via POST /documents, put one in uploaded_docs/, or pass a path:")
    print("  python experiments/day13_pdf_parsing.py path/to/file.pdf")
    sys.exit(1)


def main():
    pdf_path = find_pdf()
    if not pdf_path.exists():
        print(f"Error: file not found: {pdf_path}")
        sys.exit(1)

    print(f"Opening: {pdf_path}\n")
    reader = PdfReader(str(pdf_path))

    total_chars = 0
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        total_chars += len(text)
        preview = text[:200].replace("\n", " ")
        print(f"Page {i}")
        print(f"  Characters: {len(text)}")
        print(f"  Preview: {preview}")
        print()

    page_count = len(reader.pages)
    print(f"Total pages: {page_count}")
    print(f"Total characters: {total_chars}")

    if page_count > 0 and total_chars / page_count < EMPTY_PAGE_THRESHOLD:
        print()
        print(
            "Warning: little to no text extracted - this PDF might be "
            "scanned/image-based and need OCR."
        )


if __name__ == "__main__":
    main()
