"""PDF text extraction."""

from __future__ import annotations

from pathlib import Path


def extract_pdf_pages(path: str | Path, password: str | None = None) -> list[tuple[int, str]]:
    """Extract page text from a PDF file using pypdf.

    Returns ``(page_number, text)`` tuples with 1-based page numbers.
    """
    from pypdf import PdfReader

    pdf_path = Path(path)
    reader = PdfReader(str(pdf_path))
    if reader.is_encrypted:
        if not password:
            raise ValueError("PDF is encrypted; pass --password or use interactive password entry.")
        if reader.decrypt(password) == 0:
            raise ValueError("Could not decrypt PDF with the provided password.")

    pages: list[tuple[int, str]] = []
    for index, page in enumerate(reader.pages, start=1):
        pages.append((index, page.extract_text() or ""))
    return pages


def extract_text_file(path: str | Path) -> list[tuple[None, str]]:
    """Read plain text as a one-page source for testing parser rules."""
    return [(None, Path(path).read_text(encoding="utf-8"))]
