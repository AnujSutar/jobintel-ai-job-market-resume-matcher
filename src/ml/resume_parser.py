"""In-memory text extraction for uploaded PDF and DOCX resumes."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import BinaryIO

from docx import Document
from pypdf import PdfReader


class ResumeReadError(ValueError):
    """Raised when an uploaded resume cannot be read as its declared format."""


def _read_pdf(file_data: bytes) -> str:
    """Extract text from all readable PDF pages without saving the upload."""
    try:
        reader = PdfReader(BytesIO(file_data))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as error:  # pypdf exceptions vary by malformed-file condition.
        raise ResumeReadError("The PDF could not be read. Try a text-based, non-password-protected PDF.") from error
    return text.strip()


def _read_docx(file_data: bytes) -> str:
    """Extract paragraph and table text from a DOCX resume in memory."""
    try:
        document = Document(BytesIO(file_data))
        paragraphs = [paragraph.text for paragraph in document.paragraphs]
        cells = [cell.text for table in document.tables for row in table.rows for cell in row.cells]
    except Exception as error:
        raise ResumeReadError("The DOCX file could not be read. Try re-saving it as a standard .docx file.") from error
    return "\n".join(paragraphs + cells).strip()


def extract_resume_text(uploaded_file: BinaryIO, filename: str) -> str:
    """Read a PDF or DOCX upload and reject blank or unsupported resumes."""
    suffix = Path(filename).suffix.lower()
    file_data = uploaded_file.read()
    if not file_data:
        raise ResumeReadError("The uploaded file is empty.")
    if suffix == ".pdf":
        text = _read_pdf(file_data)
    elif suffix == ".docx":
        text = _read_docx(file_data)
    else:
        raise ResumeReadError("Upload a PDF or DOCX resume.")
    if not text:
        raise ResumeReadError("No readable text was found. Scanned-image resumes need OCR before upload.")
    return text
