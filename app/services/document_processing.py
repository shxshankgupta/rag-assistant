import re

from pypdf import PdfReader

from app.core.exceptions import ValidationError


_WHITESPACE_RE = re.compile(r"\s+")


def extract_pdf_text(file_path: str) -> str:
    try:
        reader = PdfReader(file_path)
    except Exception as exc:  # pragma: no cover - parser-specific failures vary
        raise ValidationError("The uploaded file is not a readable PDF.") from exc

    pages: list[str] = []
    for page in reader.pages:
        try:
            page_text = page.extract_text() or ""
        except Exception:
            page_text = ""
        if page_text:
            pages.append(page_text)

    text = "\n\n".join(pages)
    normalized = _WHITESPACE_RE.sub(" ", text).strip()
    if not normalized:
        raise ValidationError("The PDF contains no extractable text.")
    return normalized


def chunk_text(text: str, *, chunk_size: int, chunk_overlap: int) -> list[str]:
    normalized = _WHITESPACE_RE.sub(" ", text).strip()
    if not normalized:
        return []

    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")

    overlap = max(0, min(chunk_overlap, max(0, chunk_size - 50)))
    chunks: list[str] = []
    start = 0
    text_length = len(normalized)

    while start < text_length:
        end = min(text_length, start + chunk_size)
        if end < text_length:
            split_at = normalized.rfind(" ", start + max(1, chunk_size // 2), end)
            if split_at > start:
                end = split_at

        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= text_length:
            break

        start = max(start + 1, end - overlap)
        while start < text_length and normalized[start].isspace():
            start += 1

    return chunks
