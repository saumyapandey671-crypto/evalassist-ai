"""
extract.py – text extraction from TXT, PDF, and DOCX files.
Supports: .txt, .pdf, .docx
Max file size: 8 MB (enforced by the caller / Flask route).
"""

from __future__ import annotations

import io
import os

SUPPORTED_EXTENSIONS = {".txt", ".pdf", ".docx"}
MAX_BYTES = 8 * 1024 * 1024  # 8 MB


class ExtractionError(ValueError):
    """Raised when a file cannot be read or is unsupported."""


def _ext(filename: str) -> str:
    return os.path.splitext(filename)[1].lower()


def extract_text(file_bytes: bytes, filename: str) -> str:
    """
    Extract plain text from *file_bytes* whose original name is *filename*.

    Returns a non-empty string or raises ExtractionError.
    """
    ext = _ext(filename)

    if ext not in SUPPORTED_EXTENSIONS:
        raise ExtractionError(
            f"Unsupported file type '{ext}'. "
            "Please upload a .txt, .pdf, or .docx file."
        )

    if len(file_bytes) > MAX_BYTES:
        raise ExtractionError(
            f"File is {len(file_bytes) // (1024*1024):.1f} MB – "
            "maximum allowed size is 8 MB."
        )

    if ext == ".txt":
        return _from_txt(file_bytes)
    if ext == ".pdf":
        return _from_pdf(file_bytes)
    if ext == ".docx":
        return _from_docx(file_bytes)

    raise ExtractionError("Unexpected extraction error.")  # pragma: no cover


def _from_txt(data: bytes) -> str:
    try:
        return data.decode("utf-8", errors="replace").strip()
    except Exception as exc:
        raise ExtractionError(f"Could not read text file: {exc}") from exc


def _from_pdf(data: bytes) -> str:
    try:
        import pypdf  # lazy import so tests don't require pypdf if not testing PDF

        reader = pypdf.PdfReader(io.BytesIO(data))
        pages = [page.extract_text() or "" for page in reader.pages]
        text = "\n".join(pages).strip()
        if not text or len(text) < 20:
            raise ExtractionError(
                "Almost no text could be extracted from this PDF. "
                "It may be a scanned document; OCR is not supported."
            )
        return text
    except ExtractionError:
        raise
    except Exception as exc:
        raise ExtractionError(f"Could not read PDF: {exc}") from exc


def _from_docx(data: bytes) -> str:
    try:
        import docx  # python-docx

        doc = docx.Document(io.BytesIO(data))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        text = "\n".join(paragraphs).strip()
        if not text:
            raise ExtractionError("The Word document appears to be empty.")
        return text
    except ExtractionError:
        raise
    except Exception as exc:
        raise ExtractionError(f"Could not read DOCX: {exc}") from exc
