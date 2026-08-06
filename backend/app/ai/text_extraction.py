"""Text extraction: turns raw PDF/DOCX bytes into plain text."""

import io

import pdfplumber
from docx import Document

from app.models.resume import FileType


class TextExtractionError(Exception):
    pass


def extract_text_from_pdf(file_bytes: bytes) -> str:
    try:
        pages_text: list[str] = []
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    pages_text.append(page_text)
        return "\n".join(pages_text)
    except Exception as exc:
        raise TextExtractionError(f"Failed to extract text from PDF: {exc}") from exc


def extract_text_from_docx(file_bytes: bytes) -> str:
    try:
        document = Document(io.BytesIO(file_bytes))
        paragraphs = [p.text for p in document.paragraphs if p.text.strip()]
        return "\n".join(paragraphs)
    except Exception as exc:
        raise TextExtractionError(f"Failed to extract text from DOCX: {exc}") from exc


def extract_text(file_bytes: bytes, file_type: FileType) -> str:
    if file_type == FileType.PDF:
        return extract_text_from_pdf(file_bytes)
    if file_type == FileType.DOCX:
        return extract_text_from_docx(file_bytes)
    raise TextExtractionError(f"Unsupported file type for extraction: {file_type}")
