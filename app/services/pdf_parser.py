from pypdf import PdfReader

EMPTY_PAGE_THRESHOLD = 20


def extract_text_from_pdf(pdf_path) -> tuple[list[dict], bool]:
    reader = PdfReader(str(pdf_path))
    pages = []
    total_chars = 0
    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        total_chars += len(text)
        pages.append({"page_number": page_number, "text": text})

    page_count = len(pages)
    near_empty = page_count > 0 and (total_chars / page_count) < EMPTY_PAGE_THRESHOLD
    return pages, near_empty
