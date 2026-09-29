"""RAG value objects."""

from pydantic import BaseModel, Field


class DocumentChunk(BaseModel):
    id: str  # f"{document_id}:{index}"
    user_id: str
    document_id: str
    document_name: str
    index: int
    text: str
    # Bumped when the source document changes, so stale chunks are replaced rather than mixed in.
    version: str = ""


class RetrievedChunk(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    text: str
    score: float = Field(ge=-1, le=1)


class IngestionReport(BaseModel):
    indexed: list[str] = Field(default_factory=list)
    skipped: list[str] = Field(default_factory=list)
    failed: dict[str, str] = Field(default_factory=dict)
