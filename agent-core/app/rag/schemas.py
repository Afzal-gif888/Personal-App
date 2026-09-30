"""Document search results, as returned by the backend's POST /documents/search."""

from pydantic import BaseModel, Field


class RetrievedChunk(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    page_number: int | None = None  # PDFs only; never guessed
    chunk_index: int = 0
    text: str
    score: float = Field(ge=-1, le=1)  # cosine similarity

    @property
    def source(self) -> str:
        return f"{self.document_name}, page {self.page_number}" if self.page_number else self.document_name
