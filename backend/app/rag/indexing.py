"""Document indexing and semantic search over PostgreSQL + pgvector.

    upload -> extract text (per page) -> chunk -> Gemini embeddings (once) -> document_chunks
    search -> embed the query -> cosine distance in pgvector, scoped to the signed-in user

Indexing runs after the upload response (a background task) and in the scheduler, which picks up
anything pending, retries failures with a back-off and re-indexes documents embedded with a
different model. Every search is filtered by the authenticated user's id.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import delete, or_, select, text, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.timeutils import utcnow
from app.db.session import SessionLocal
from app.models import Document, DocumentChunk, User
from app.models.enums import DocumentIndexStatus, DocumentStatus
from app.models.platform import EMBEDDING_DIMENSIONS
from app.rag.chunking import INDEXABLE_TYPES, ExtractionError, chunk_pages, extract_pages
from app.rag.embeddings import EmbeddingError, EmbeddingProvider, get_embedding_provider
from app.storage import get_storage

logger = logging.getLogger(__name__)

MAX_INDEX_ATTEMPTS = 5
RETRY_AFTER = timedelta(minutes=10)
STALE_INDEXING = timedelta(minutes=15)
NO_RESULTS = "No relevant document content found."


class DocumentSearchUnavailable(AppError):
    """Document search is unavailable right now."""

    status_code = 503
    code = "DOCUMENT_SEARCH_UNAVAILABLE"


# --- indexing -------------------------------------------------------------------------------------


def _claim(db: Session, doc_id: uuid.UUID, *, allow_indexed: bool = False) -> bool:
    """Atomically move the document to INDEXING, so two workers never index it at once."""
    allowed = [DocumentIndexStatus.PENDING, DocumentIndexStatus.FAILED]
    if allow_indexed:
        allowed.append(DocumentIndexStatus.INDEXED)
    result = db.execute(
        update(Document)
        .where(Document.id == doc_id, Document.status == DocumentStatus.READY, Document.index_status.in_(allowed))
        .values(index_status=DocumentIndexStatus.INDEXING, index_started_at=utcnow(),
                index_attempts=Document.index_attempts + 1)
    )
    db.commit()
    return getattr(result, "rowcount", 0) == 1


def _finish(db: Session, doc_id: uuid.UUID, status: DocumentIndexStatus, error: str | None = None,
            *, final: bool = False) -> DocumentIndexStatus:
    db.rollback()
    doc = db.get_one(Document, doc_id)
    doc.index_status = status
    doc.index_error = error
    if final:  # retrying can't help (unreadable file): stop the scheduler from trying again
        doc.index_attempts = MAX_INDEX_ATTEMPTS
    db.commit()
    return status


def index_document(doc_id: uuid.UUID, *, allow_indexed: bool = False) -> DocumentIndexStatus | None:
    """Index one document in its own session. Returns the resulting status, or None if another
    worker has it (or it isn't ready). Never raises: failures are recorded on the document."""
    with SessionLocal() as db:
        if not _claim(db, doc_id, allow_indexed=allow_indexed):
            return None
        doc = db.get_one(Document, doc_id)
        try:
            return _index(db, doc)
        except ExtractionError as exc:
            return _finish(db, doc_id, DocumentIndexStatus.FAILED, str(exc), final=True)
        except EmbeddingError as exc:
            logger.warning("Document indexing failed", extra={"document_id": str(doc_id), "code": exc.code})
            return _finish(db, doc_id, DocumentIndexStatus.FAILED, exc.message)
        except Exception:
            logger.exception("Document indexing crashed", extra={"document_id": str(doc_id)})
            return _finish(db, doc_id, DocumentIndexStatus.FAILED, "Indexing failed unexpectedly.")


def _index(db: Session, doc: Document) -> DocumentIndexStatus:
    settings = get_settings()
    if doc.mime_type not in INDEXABLE_TYPES:
        return _finish(db, doc.id, DocumentIndexStatus.UNSUPPORTED,
                       "Only PDF and text files can be searched.", final=True)
    pages = extract_pages(get_storage().path(doc.storage_key), doc.mime_type)
    chunks = chunk_pages(pages, max_chars=settings.document_chunk_chars, overlap=settings.document_chunk_overlap)
    if not chunks:
        return _finish(db, doc.id, DocumentIndexStatus.UNSUPPORTED,
                       "No text found in this file (scanned PDFs have no text layer).", final=True)

    provider = get_embedding_provider()
    if provider.dimensions != EMBEDDING_DIMENSIONS:
        raise EmbeddingError(f"EMBEDDING_DIMENSIONS={provider.dimensions} but the index stores {EMBEDDING_DIMENSIONS}.",
                             code="EMBEDDING_DIMENSION_MISMATCH")

    # Same text, same model: the stored embeddings are still valid, so don't pay for new ones.
    existing = db.execute(
        select(DocumentChunk.chunk_index, DocumentChunk.content_hash).where(DocumentChunk.document_id == doc.id)
    ).all()
    if doc.embedding_model == provider.index_version and sorted(existing) == [(c.index, c.content_hash) for c in chunks]:
        return _mark_indexed(db, doc, provider, len(chunks))

    vectors = provider.embed_documents([c.content for c in chunks], title=doc.original_filename)
    # Replace, never append: re-indexing can't leave duplicate chunks (also unique per document+index).
    db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == doc.id))
    db.add_all(
        DocumentChunk(
            user_id=doc.user_id,
            document_id=doc.id,
            chunk_index=c.index,
            content=c.content,
            content_hash=c.content_hash,
            page_number=c.page_number,
            character_count=len(c.content),
            embedding=vector,
            meta={"filename": doc.original_filename, "page": c.page_number, "mimeType": doc.mime_type},
        )
        for c, vector in zip(chunks, vectors, strict=True)
    )
    return _mark_indexed(db, doc, provider, len(chunks))


def _mark_indexed(db: Session, doc: Document, provider: EmbeddingProvider, count: int) -> DocumentIndexStatus:
    doc.index_status = DocumentIndexStatus.INDEXED
    doc.index_error = None
    doc.chunk_count = count
    doc.embedding_model = provider.index_version
    doc.indexed_at = utcnow()
    db.commit()
    logger.info("Document indexed", extra={"document_id": str(doc.id), "chunks": count, "model": provider.index_version})
    return DocumentIndexStatus.INDEXED


def reindex_request(db: Session, doc: Document) -> None:
    """Queue a document for a fresh attempt (manual retry)."""
    doc.index_status = DocumentIndexStatus.PENDING
    doc.index_attempts = 0
    doc.index_error = None
    db.commit()


def index_pending(db: Session, *, limit: int = 5) -> int:
    """Scheduler job: index pending documents, retry failures, re-index after a model change."""
    now = utcnow()
    # A worker that died mid-way leaves INDEXING behind; hand those back.
    db.execute(
        update(Document)
        .where(Document.index_status == DocumentIndexStatus.INDEXING, Document.index_started_at < now - STALE_INDEXING)
        .values(index_status=DocumentIndexStatus.FAILED, index_error="Indexing was interrupted.")
    )
    db.commit()
    if not get_settings().embeddings_configured:
        return 0
    version = get_embedding_provider().index_version
    ids = db.scalars(
        select(Document.id)
        .where(
            Document.status == DocumentStatus.READY,
            or_(
                Document.index_status == DocumentIndexStatus.PENDING,
                (Document.index_status == DocumentIndexStatus.FAILED)
                & (Document.index_attempts < MAX_INDEX_ATTEMPTS)
                & (Document.index_started_at < now - RETRY_AFTER),
                (Document.index_status == DocumentIndexStatus.INDEXED) & (Document.embedding_model != version),
            ),
        )
        .order_by(Document.uploaded_at)
        .limit(limit)
    ).all()
    done = 0
    for doc_id in ids:
        done += index_document(doc_id, allow_indexed=True) == DocumentIndexStatus.INDEXED
    return done


# --- search ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class SearchHit:
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_name: str
    chunk_index: int
    page_number: int | None
    content: str
    similarity: float


def search(db: Session, user: User, query: str, *, top_k: int | None = None,
           document_ids: list[uuid.UUID] | None = None) -> list[SearchHit]:
    """Semantic search over the user's own indexed documents. Only this user's chunks can match."""
    settings = get_settings()
    if db.get_bind().dialect.name != "postgresql":
        raise DocumentSearchUnavailable("Document search needs PostgreSQL with pgvector.")
    provider = get_embedding_provider()
    vector = provider.embed_query(query)  # the only embedding call a search makes

    distance = DocumentChunk.embedding.cosine_distance(vector)
    stmt = (
        select(DocumentChunk, Document.original_filename, distance.label("distance"))
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(
            DocumentChunk.user_id == user.id,  # the ownership filter; never taken from the request
            Document.user_id == user.id,
            Document.status == DocumentStatus.READY,
            Document.index_status == DocumentIndexStatus.INDEXED,
            Document.embedding_model == provider.index_version,  # other models' vectors aren't comparable
        )
        .order_by(distance)
        .limit(top_k or settings.document_search_top_k)
    )
    if document_ids:
        stmt = stmt.where(DocumentChunk.document_id.in_(document_ids))
    try:
        # With the user filter, keep scanning the HNSW index until enough rows match (pgvector >= 0.8).
        db.execute(text("SET LOCAL hnsw.iterative_scan = strict_order"))
        rows = db.execute(stmt).all()
    except DBAPIError as exc:
        db.rollback()
        logger.error("Vector search failed", extra={"error": type(exc.orig).__name__ if exc.orig else "DBAPIError"})
        raise DocumentSearchUnavailable("Document search is unavailable right now.") from exc
    hits = [
        SearchHit(chunk_id=chunk.id, document_id=chunk.document_id, document_name=name,
                  chunk_index=chunk.chunk_index, page_number=chunk.page_number, content=chunk.content,
                  similarity=round(1 - float(dist), 4))
        for chunk, name, dist in rows
    ]
    return [h for h in hits if h.similarity >= settings.document_search_min_similarity]
