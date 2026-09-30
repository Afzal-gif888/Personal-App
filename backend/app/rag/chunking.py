"""Text extraction and deterministic chunking.

PDFs are read page by page and chunks never cross a page, so every chunk has an exact page number.
The same file and settings always give the same chunks (same order, text and hashes).
"""

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

TEXT_TYPES = {"text/plain", "text/markdown", "text/csv"}
PDF_TYPE = "application/pdf"
INDEXABLE_TYPES = TEXT_TYPES | {PDF_TYPE}


class ExtractionError(Exception):
    """The file couldn't be read (malformed or encrypted)."""


@dataclass(frozen=True)
class Page:
    number: int | None  # 1-based for PDFs; None for plain text files
    text: str


@dataclass(frozen=True)
class Chunk:
    index: int
    page_number: int | None
    content: str

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(self.content.encode("utf-8")).hexdigest()


def extract_pages(path: Path, mime_type: str) -> list[Page]:
    mime = mime_type.split(";")[0].strip().lower()
    if mime in TEXT_TYPES:
        return [Page(None, path.read_bytes().decode("utf-8", errors="replace"))]
    if mime == PDF_TYPE:
        from pypdf import PdfReader
        from pypdf.errors import PdfReadError

        try:
            reader = PdfReader(str(path))
            return [Page(i, page.extract_text() or "") for i, page in enumerate(reader.pages, start=1)]
        except (PdfReadError, ValueError, KeyError, OSError) as exc:
            raise ExtractionError("Could not read this PDF. It may be corrupted or password-protected.") from exc
    raise ExtractionError(f"Text can't be extracted from {mime} files.")


def _normalise(text: str) -> str:
    text = text.replace("\x00", "")
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def split_text(text: str, *, max_chars: int, overlap: int) -> list[str]:
    """Paragraph-aware pieces of at most `max_chars`, carrying `overlap` characters forward."""
    text = _normalise(text)
    if not text:
        return []
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    pieces: list[str] = []
    for para in paragraphs:
        while len(para) > max_chars:  # split an oversized paragraph at a sentence or word boundary
            cut = max(para.rfind(". ", 0, max_chars), para.rfind(" ", 0, max_chars))
            cut = cut + 1 if cut > max_chars // 2 else max_chars
            pieces.append(para[:cut].strip())
            para = para[cut:].strip()
        if para:
            pieces.append(para)

    chunks: list[str] = []
    current = ""
    for piece in pieces:
        if current and len(current) + len(piece) + 2 > max_chars:
            chunks.append(current)
            tail = current[-overlap:] if overlap else ""
            # Start the overlap at a word boundary so chunks don't begin mid-word.
            tail = tail[tail.find(" ") + 1:] if " " in tail else tail
            current = f"{tail}\n\n{piece}" if tail and len(tail) + len(piece) + 2 <= max_chars else piece
        else:
            current = f"{current}\n\n{piece}" if current else piece
    if current:
        chunks.append(current)
    return chunks


def chunk_pages(pages: list[Page], *, max_chars: int, overlap: int) -> list[Chunk]:
    chunks: list[Chunk] = []
    for page in pages:
        for content in split_text(page.text, max_chars=max_chars, overlap=overlap):
            chunks.append(Chunk(index=len(chunks), page_number=page.number, content=content))
    return chunks
