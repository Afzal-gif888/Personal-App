"""Document ingestion and retrieval pipeline.

    backend document  ->  text extraction  ->  chunking  ->  embeddings  ->  VectorStore
    user question     ->  embedding  ->  VectorStore.search  ->  relevant chunks  ->  agent state

Documents are downloaded through the backend API with the user's token, so the Agent Core only
ever indexes files that user is allowed to read.
"""

import io
import logging
import re

from app.backend.client import BackendClient
from app.backend.exceptions import BackendError
from app.backend.schemas import Document
from app.config.settings import Settings
from app.rag.embeddings import EmbeddingProvider, create_embedding_provider
from app.rag.retriever import Retriever, VectorStore, create_vector_store
from app.rag.schemas import DocumentChunk, IngestionReport, RetrievedChunk

logger = logging.getLogger(__name__)

TEXT_TYPES = {"text/plain", "text/markdown", "text/csv"}
PDF_TYPE = "application/pdf"
SUPPORTED_TYPES = TEXT_TYPES | {PDF_TYPE}
MAX_INDEXED_DOCUMENTS = 50


class ExtractionError(Exception):
    pass


def extract_text(data: bytes, mime_type: str) -> str:
    mime = mime_type.split(";")[0].strip().lower()
    if mime in TEXT_TYPES:
        return data.decode("utf-8", errors="replace")
    if mime == PDF_TYPE:
        from pypdf import PdfReader
        from pypdf.errors import PdfReadError

        try:
            reader = PdfReader(io.BytesIO(data))
            return "\n\n".join(page.extract_text() or "" for page in reader.pages)
        except (PdfReadError, ValueError, KeyError) as exc:
            raise ExtractionError("Could not read this PDF.") from exc
    raise ExtractionError(f"Unsupported document type: {mime}")


def chunk_text(text: str, *, max_chars: int = 900, overlap: int = 150) -> list[str]:
    """Paragraph-aware chunks of at most `max_chars`, with `overlap` characters carried forward."""
    text = re.sub(r"[ \t]+", " ", text).strip()
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
        if current and len(current) + 2 + len(piece) > max_chars:
            chunks.append(current)
            tail = current[-overlap:] if overlap else ""
            tail = tail[tail.find(" ") + 1 :] if " " in tail else tail
            current = f"{tail}\n\n{piece}".strip() if tail else piece
            if len(current) > max_chars:
                current = piece
        else:
            current = f"{current}\n\n{piece}" if current else piece
    if current:
        chunks.append(current)
    return chunks


class DocumentIngestionPipeline:
    def __init__(self, store: VectorStore, embedder: EmbeddingProvider, *, chunk_chars: int, overlap: int, max_bytes: int) -> None:
        self.store = store
        self.embedder = embedder
        self.chunk_chars = chunk_chars
        self.overlap = overlap
        self.max_bytes = max_bytes

    @staticmethod
    def version_of(doc: Document) -> str:
        return f"{doc.size}:{doc.processed_at.isoformat() if doc.processed_at else ''}"

    async def index_text(self, user_id: str, document_id: str, document_name: str, text: str, *, version: str = "") -> int:
        pieces = chunk_text(text, max_chars=self.chunk_chars, overlap=self.overlap)
        await self.store.delete_document(user_id, document_id)
        if not pieces:
            return 0
        chunks = [
            DocumentChunk(id=f"{document_id}:{i}", user_id=user_id, document_id=document_id,
                          document_name=document_name, index=i, text=p, version=version)
            for i, p in enumerate(pieces)
        ]
        await self.store.upsert(chunks, await self.embedder.embed(pieces))
        return len(chunks)

    async def ensure_indexed(self, backend: BackendClient, user_id: str) -> IngestionReport:
        """Index the user's ready documents that are new or changed since they were last indexed."""
        report = IngestionReport()
        page = await backend.list_documents(status="ready", page_size=MAX_INDEXED_DOCUMENTS)
        for doc in page.items:
            if doc.mime_type not in SUPPORTED_TYPES:
                report.skipped.append(doc.id)
                continue
            version = self.version_of(doc)
            if await self.store.document_version(user_id, doc.id) == version:
                report.skipped.append(doc.id)
                continue
            try:
                data, _ = await backend.download_document(doc.id, max_bytes=self.max_bytes)
                count = await self.index_text(user_id, doc.id, doc.name, extract_text(data, doc.mime_type), version=version)
                (report.indexed if count else report.skipped).append(doc.id)
            except (ExtractionError, BackendError) as exc:
                logger.warning("Document indexing failed", extra={"document_id": doc.id, "error": type(exc).__name__})
                report.failed[doc.id] = str(exc) if isinstance(exc, ExtractionError) else "download failed"
        return report


class RagService:
    """What the agent and document tools use: keep the index fresh, then retrieve."""

    def __init__(self, pipeline: DocumentIngestionPipeline, retriever: Retriever) -> None:
        self.pipeline = pipeline
        self.retriever = retriever

    async def search(
        self, backend: BackendClient, user_id: str, query: str, *, k: int | None = None, document_ids: list[str] | None = None
    ) -> list[RetrievedChunk]:
        await self.pipeline.ensure_indexed(backend, user_id)
        return await self.retriever.retrieve(user_id, query, k=k, document_ids=document_ids)


def create_rag_service(settings: Settings) -> RagService:
    store = create_vector_store(settings)
    embedder = create_embedding_provider(settings)
    pipeline = DocumentIngestionPipeline(
        store, embedder, chunk_chars=settings.rag_chunk_chars, overlap=settings.rag_chunk_overlap,
        max_bytes=settings.rag_max_document_mb * 1024 * 1024,
    )
    return RagService(pipeline, Retriever(store, embedder, top_k=settings.rag_top_k, min_score=settings.rag_min_score))
