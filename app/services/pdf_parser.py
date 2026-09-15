import logging

from pypdf import PdfReader
from pypdf.errors import PdfReadError, PdfStreamError

logger = logging.getLogger(__name__)

EMPTY_PAGE_THRESHOLD = 20


class InvalidPdfError(Exception):
    """Raised when a file cannot be read as a PDF."""


def extract_text_from_pdf(pdf_path) -> tuple[list[dict], bool]:
    """Extract per-page text from a PDF.

    Returns (pages, near_empty). Each page is {"page_number", "text"}.
    near_empty is True when little or no selectable text was found
    (typical of scanned/image PDFs that need OCR).
    """
    try:
        reader = PdfReader(str(pdf_path))
    except (PdfReadError, PdfStreamError, OSError, ValueError) as exc:
        raise InvalidPdfError(f"File is not a valid PDF: {pdf_path}") from exc

    pages = []
    total_chars = 0
    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        total_chars += len(text)
        pages.append({"page_number": page_number, "text": text})

    page_count = len(pages)
    near_empty = page_count == 0 or (total_chars / page_count) < EMPTY_PAGE_THRESHOLD
    if near_empty:
        logger.warning("Little to no text extracted from %s (pages=%s, chars=%s)", pdf_path, page_count, total_chars)
    else:
        logger.info("Extracted text from %s (%s pages, %s chars)", pdf_path, page_count, total_chars)
    return pages, near_empty
