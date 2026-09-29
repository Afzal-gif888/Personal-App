"""Vector storage and retrieval.

`VectorStore` is the storage abstraction. The bundled `InMemoryVectorStore` is namespaced per user
so one user's chunks can never be returned for another user's query. A pgvector-backed store
belongs behind the backend's API (the Agent Core must not open database connections itself); it
would implement this same interface by calling that API.
"""

import asyncio
import math
import re
from abc import ABC, abstractmethod

from app.config.settings import Settings
from app.rag.embeddings import EmbeddingProvider
from app.rag.schemas import DocumentChunk, RetrievedChunk

# Words that say *where* to look ("according to my uploaded notes") rather than *what* to look for.
# They are dropped from queries only, so they don't dilute the match against document text.
_QUERY_NOISE = re.compile(
    r"\b(according|uploaded|upload|notes?|documents?|docs?|pdfs?|slides?|files?|explain|summari[sz]e|tell|say|says)\b",
    re.IGNORECASE,
)


def clean_query(query: str) -> str:
    cleaned = " ".join(_QUERY_NOISE.sub(" ", query).split())
    return cleaned or query


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


class VectorStore(ABC):
    @abstractmethod
    async def upsert(self, chunks: list[DocumentChunk], embeddings: list[list[float]]) -> None: ...

    @abstractmethod
    async def search(
        self, user_id: str, embedding: list[float], *, k: int, document_ids: list[str] | None = None
    ) -> list[tuple[DocumentChunk, float]]: ...

    @abstractmethod
    async def delete_document(self, user_id: str, document_id: str) -> None: ...

    @abstractmethod
    async def document_version(self, user_id: str, document_id: str) -> str | None:
        """Version of the indexed copy, or None when the document is not indexed."""


class InMemoryVectorStore(VectorStore):
    def __init__(self) -> None:
        self._rows: dict[str, dict[str, tuple[DocumentChunk, list[float]]]] = {}
        self._lock = asyncio.Lock()

    async def upsert(self, chunks: list[DocumentChunk], embeddings: list[list[float]]) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must have the same length")
        async with self._lock:
            for chunk, emb in zip(chunks, embeddings, strict=False):
                self._rows.setdefault(chunk.user_id, {})[chunk.id] = (chunk, emb)

    async def search(
        self, user_id: str, embedding: list[float], *, k: int, document_ids: list[str] | None = None
    ) -> list[tuple[DocumentChunk, float]]:
        rows = self._rows.get(user_id, {}).values()
        wanted = set(document_ids) if document_ids else None
        scored = [(c, cosine(embedding, e)) for c, e in rows if wanted is None or c.document_id in wanted]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]

    async def delete_document(self, user_id: str, document_id: str) -> None:
        async with self._lock:
            rows = self._rows.get(user_id, {})
            for key in [k for k, (c, _) in rows.items() if c.document_id == document_id]:
                del rows[key]

    async def document_version(self, user_id: str, document_id: str) -> str | None:
        for chunk, _ in self._rows.get(user_id, {}).values():
            if chunk.document_id == document_id:
                return chunk.version
        return None

    def chunk_count(self, user_id: str) -> int:
        return len(self._rows.get(user_id, {}))


class Retriever:
    def __init__(self, store: VectorStore, embedder: EmbeddingProvider, *, top_k: int = 4, min_score: float = 0.12) -> None:
        self.store = store
        self.embedder = embedder
        self.top_k = top_k
        self.min_score = min_score

    async def retrieve(
        self, user_id: str, query: str, *, k: int | None = None, document_ids: list[str] | None = None
    ) -> list[RetrievedChunk]:
        """The most relevant chunks above `min_score`; an empty list means nothing relevant."""
        [embedding] = await self.embedder.embed([clean_query(query)])
        hits = await self.store.search(user_id, embedding, k=k or self.top_k, document_ids=document_ids)
        return [
            RetrievedChunk(
                chunk_id=c.id, document_id=c.document_id, document_name=c.document_name, text=c.text,
                score=round(max(-1.0, min(1.0, score)), 4),
            )
            for c, score in hits
            if score >= self.min_score
        ]


def create_vector_store(settings: Settings) -> VectorStore:
    # "" and "memory" both select the in-process store; see the module docstring for pgvector.
    return InMemoryVectorStore()
