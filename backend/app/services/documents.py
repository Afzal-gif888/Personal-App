import logging
import uuid
from pathlib import PurePath
from typing import BinaryIO

from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError, NotFoundError, ValidationFailed
from app.core.timeutils import utcnow
from app.models import Document, User
from app.models.enums import DocumentStatus
from app.repositories.base import apply_patch, get_owned, paginate
from app.schemas.platform import DocumentOut, DocumentUpdate
from app.services import audit
from app.storage import get_storage

logger = logging.getLogger(__name__)

# Extension -> canonical MIME type. The browser-supplied content type is not trusted.
ALLOWED_TYPES = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".csv": "text/csv",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}
_MAGIC = {
    ".pdf": (b"%PDF",),
    ".png": (b"\x89PNG",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".docx": (b"PK\x03\x04",),
    ".pptx": (b"PK\x03\x04",),
    ".xlsx": (b"PK\x03\x04",),
}


class UnsupportedMediaType(AppError):
    """Unsupported file type"""

    status_code = 415
    code = "UNSUPPORTED_MEDIA_TYPE"


def to_out(doc: Document) -> DocumentOut:
    return DocumentOut(
        id=doc.id,
        name=doc.original_filename,
        mime_type=doc.mime_type,
        size=doc.size,
        category=doc.category,
        status=doc.status,
        page_count=doc.page_count,
        checksum_sha256=doc.checksum_sha256,
        error_message=doc.error_message,
        uploaded_at=doc.uploaded_at,
        processed_at=doc.processed_at,
        download_url=f"/api/v1/documents/{doc.id}/download",
    )


def list_documents(
    db: Session,
    user: User,
    *,
    page: int,
    page_size: int,
    category: str | None = None,
    status: DocumentStatus | None = None,
    q: str | None = None,
) -> tuple[list[Document], int]:
    stmt = select(Document).where(Document.user_id == user.id, Document.status != DocumentStatus.DELETED)
    if category:
        stmt = stmt.where(Document.category == category)
    if status:
        stmt = stmt.where(Document.status == status)
    if q:
        stmt = stmt.where(Document.original_filename.ilike(f"%{q.strip()}%"))
    return paginate(db, stmt.order_by(Document.uploaded_at.desc()), page, page_size)


def get_document(db: Session, user: User, doc_id: uuid.UUID) -> Document:
    doc = get_owned(db, Document, doc_id, user.id, label="Document")
    if doc.status == DocumentStatus.DELETED:
        raise NotFoundError("Document not found")
    return doc


def upload(db: Session, user: User, filename: str, stream: BinaryIO, category: str | None) -> Document:
    name = PurePath(filename or "").name.strip()[:255]
    ext = PurePath(name).suffix.lower()
    if not name or ext not in ALLOWED_TYPES:
        raise UnsupportedMediaType(f"Allowed file types: {', '.join(sorted(ALLOWED_TYPES))}")

    head = stream.read(8)
    if ext in _MAGIC and not head.startswith(_MAGIC[ext]):
        raise UnsupportedMediaType(f"File content does not match the {ext} extension")
    stream.seek(0)

    doc_id = uuid.uuid4()
    key = f"{user.id}/{doc_id}{ext}"
    stored = get_storage().save(key, stream, max_bytes=get_settings().max_upload_bytes)
    if stored.size == 0:
        get_storage().delete(key)
        raise ValidationFailed("File is empty")

    doc = Document(
        id=doc_id,
        user_id=user.id,
        filename=f"{doc_id}{ext}",
        original_filename=name,
        mime_type=ALLOWED_TYPES[ext],
        size=stored.size,
        storage_key=key,
        category=(category or "General").strip()[:100] or "General",
        status=DocumentStatus.PROCESSING,
        checksum_sha256=stored.sha256,
    )
    db.add(doc)
    try:
        db.flush()
    except Exception:
        get_storage().delete(key)
        raise
    _process(doc)
    db.commit()
    return doc


def _process(doc: Document) -> None:
    """Extract metadata synchronously. Small uploads make this cheap; move to a job queue if it grows."""
    try:
        if doc.mime_type == "application/pdf":
            reader = PdfReader(str(get_storage().path(doc.storage_key)))
            doc.page_count = len(reader.pages)
        doc.status = DocumentStatus.READY
    except Exception as exc:  # malformed files are the user's problem, not a server error
        logger.warning("Document processing failed", extra={"document_id": str(doc.id), "error": str(exc)})
        doc.status = DocumentStatus.FAILED
        doc.error_message = "Could not read this file. It may be corrupted or password-protected."
    doc.processed_at = utcnow()


def update_document(db: Session, user: User, doc_id: uuid.UUID, data: DocumentUpdate) -> Document:
    doc = get_document(db, user, doc_id)
    patch = data.model_dump(exclude_unset=True)
    if "name" in patch:
        patch["original_filename"] = PurePath(patch.pop("name")).name
    apply_patch(doc, patch, required=("original_filename",))
    db.commit()
    return doc


def delete_document(db: Session, user: User, doc_id: uuid.UUID, *, ip: str | None = None) -> None:
    doc = get_document(db, user, doc_id)
    key = doc.storage_key
    audit.record(
        db, "document.deleted", user_id=user.id, resource_type="document", resource_id=doc.id, ip_address=ip,
        details={"name": doc.original_filename},
    )
    db.delete(doc)
    db.commit()
    get_storage().delete(key)  # after commit: a failed commit must not lose the file
