import io
import re
from pathlib import Path
from typing import Any

from .rag_store import split_content_into_chunks

SUPPORTED_UPLOAD_EXTENSIONS = {".txt", ".md", ".pdf"}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024


class IngestionError(ValueError):
    pass


def validate_upload_filename(filename: str) -> str:
    extension = Path(str(filename or "")).suffix.lower()
    if extension not in SUPPORTED_UPLOAD_EXTENSIONS:
        raise IngestionError(f"Unsupported file type: {extension or 'unknown'}")
    return extension


def validate_upload_size(content: bytes, max_bytes: int = MAX_UPLOAD_BYTES) -> None:
    if not content:
        raise IngestionError("Uploaded file is empty.")
    if len(content) > max_bytes:
        raise IngestionError(f"Uploaded file is too large. Max size is {max_bytes} bytes.")


def clean_extracted_text(text: str) -> str:
    normalized = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", normalized)
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    lines = [line.strip() for line in normalized.split("\n")]
    return "\n".join(lines).strip()


def decode_text_bytes(content: bytes) -> str:
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise IngestionError("Only UTF-8 text files are supported in this version.") from exc


def extract_pdf_text(content: bytes) -> str:
    try:
        from pypdf import PdfReader
    except Exception as exc:
        raise IngestionError("PDF parsing dependency is unavailable. Install pypdf to parse PDF files.") from exc

    try:
        reader = PdfReader(io.BytesIO(content))
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        raise IngestionError("Failed to parse PDF file.") from exc


async def extract_text_from_upload(*, filename: str, content: bytes) -> str:
    extension = validate_upload_filename(filename)
    validate_upload_size(content)
    if extension in {".txt", ".md"}:
        return clean_extracted_text(decode_text_bytes(content))
    if extension == ".pdf":
        return clean_extracted_text(extract_pdf_text(content))
    raise IngestionError(f"Unsupported file type: {extension}")


def build_ingestion_preview(text: str, *, title: str) -> dict[str, Any]:
    cleaned = clean_extracted_text(text)
    if not cleaned:
        raise IngestionError("Parsed empty text from uploaded file.")

    chunks = split_content_into_chunks(cleaned)
    if not chunks:
        raise IngestionError("No chunks generated from uploaded file.")

    warnings: list[str] = []
    if len(cleaned) < 80:
        warnings.append("文本较短，可能无法形成高质量 RAG 召回。")

    return {
        "title": title.strip(),
        "textLength": len(cleaned),
        "chunkCount": len(chunks),
        "warnings": warnings,
    }
