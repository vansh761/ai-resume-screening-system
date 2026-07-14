"""
Text extraction: turns raw PDF/DOCX bytes into plain text.

Design decision
----------------
`pdfplumber` was chosen over `pypdf` specifically for resumes: resumes
are visually structured documents (columns, indented bullet lists,
section headers), and `pdfplumber` reads text in an order that respects
layout far better than `pypdf`, which frequently scrambles reading
order on multi-column resumes. The trade-off is speed — `pdfplumber` is
slower — but that's acceptable here because parsing happens once per
upload, not on a hot request path, and from Milestone 10 onward this
runs inside a Celery worker anyway, off the request thread entirely.

Every function here works on in-memory bytes (`io.BytesIO`), not file
paths — this keeps extraction decoupled from *where* the file is
stored (local disk today, S3 later), which is exactly the separation
`app/services/storage/` was built to provide.
"""

import io

import pdfplumber
from docx import Document

from app.models.resume import FileType


class TextExtractionError(Exception):
    """Raised when a file can't be parsed into text at all."""


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extracts text from a PDF, page by page.

    Pages that yield no extractable text (e.g. a scanned image with no
    text layer) contribute nothing rather than raising — a resume with
    one unreadable page shouldn't fail the whole extraction. OCR for
    fully scanned resumes is a documented future improvement, not
    something this milestone attempts.
    """
    try:
        pages_text: list[str] = []
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    pages_text.append(page_text)
        return "\n".join(pages_text)
    except Exception as exc:  # pdfplumber can raise various low-level parser errors
        raise TextExtractionError(f"Failed to extract text from PDF: {exc}") from exc


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extracts text from a DOCX, paragraph by paragraph."""
    try:
        document = Document(io.BytesIO(file_bytes))
        paragraphs = [p.text for p in document.paragraphs if p.text.strip()]
        return "\n".join(paragraphs)
    except Exception as exc:
        raise TextExtractionError(f"Failed to extract text from DOCX: {exc}") from exc


def extract_text(file_bytes: bytes, file_type: FileType) -> str:
    """Dispatches to the correct extractor based on file type."""
    if file_type == FileType.PDF:
        return extract_text_from_pdf(file_bytes)
    if file_type == FileType.DOCX:
        return extract_text_from_docx(file_bytes)
    raise TextExtractionError(f"Unsupported file type for extraction: {file_type}")
