"""Embedding providers for document search.

`GeminiEmbeddingProvider` is the only provider: there is deliberately no silent fallback to a
non-semantic embedder. When EMBEDDING_* isn't configured, indexing and search fail with a clear
error instead of pretending to work.

Gemini embedding API (REST):
    POST {base}/models/{model}:batchEmbedContents   header x-goog-api-key: <EMBEDDING_API_KEY>
    {"requests": [{"model": "models/{model}", "content": {"parts": [{"text": ...}]}, "outputDimensionality": N}]}
    -> {"embeddings": [{"values": [...]}, ...]}

Queries and passages are embedded asymmetrically. gemini-embedding-001 takes a `taskType`; newer
models (gemini-embedding-2) ignore it (verified: identical vectors) and take the task as a text
prefix instead: "task: search result | query: ..." / "title: ... | text: ...". With the prefixes
the right passage ranks first and unrelated questions score lower (measured on a real 19-page PDF).
"""

import logging
import re
import time
from abc import ABC, abstractmethod

import httpx

from app.core.config import Settings, get_settings
from app.core.errors import AppError

logger = logging.getLogger(__name__)

BATCH_SIZE = 100  # Gemini's batchEmbedContents limit
# Free-tier quotas are per minute and count every passage in a batch. Indexing (a background job)
# waits for the window to reset; an interactive search doesn't make the user wait that long.
INDEXING_MAX_WAIT_SECONDS = 70
INDEXING_RATE_LIMIT_RETRIES = 3
QUERY_MAX_WAIT_SECONDS = 3
_RETRY_DELAY = re.compile(r'"retryDelay":\s*"(\d+(?:\.\d+)?)s"')


class EmbeddingError(AppError):
    """The embedding service failed or returned something unusable."""

    status_code = 502
    code = "EMBEDDING_FAILED"


class EmbeddingRateLimited(EmbeddingError):
    """The embedding quota or rate limit was hit; retry later."""

    status_code = 429
    code = "EMBEDDING_RATE_LIMITED"


class EmbeddingNotConfigured(EmbeddingError):
    """Document search is not configured on the server."""

    status_code = 503
    code = "DOCUMENT_SEARCH_UNAVAILABLE"


class EmbeddingProvider(ABC):
    name: str
    model: str
    dimensions: int

    @property
    def index_version(self) -> str:
        return self.model

    @abstractmethod
    def embed_documents(self, texts: list[str], *, title: str | None = None) -> list[list[float]]:
        """One vector per passage, in order."""

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """The vector for a search query."""


class GeminiEmbeddingProvider(EmbeddingProvider):
    name = "gemini"

    def __init__(self, settings: Settings, *, transport: httpx.BaseTransport | None = None) -> None:
        self.model = settings.embedding_model.removeprefix("models/")
        self.dimensions = settings.embedding_dimensions
        self._url = f"{settings.embedding_base_url.rstrip('/')}/models/{self.model}:batchEmbedContents"
        self._key = settings.embedding_api_key
        self._timeout = settings.embedding_timeout_seconds
        self._transport = transport

    @property
    def index_version(self) -> str:
        """Stored per document: vectors are only comparable with the same model and text format."""
        return self.model if self._task_type_model else f"{self.model}+prompts"

    @property
    def _task_type_model(self) -> bool:
        return self.model.startswith("gemini-embedding-001")

    def embed_documents(self, texts: list[str], *, title: str | None = None) -> list[list[float]]:
        out: list[list[float]] = []
        for start in range(0, len(texts), BATCH_SIZE):
            out += self._batch(texts[start:start + BATCH_SIZE], "RETRIEVAL_DOCUMENT", title,
                               max_wait=INDEXING_MAX_WAIT_SECONDS, retries=INDEXING_RATE_LIMIT_RETRIES)
        return out

    def embed_query(self, text: str) -> list[float]:
        return self._batch([text], "RETRIEVAL_QUERY", None, max_wait=QUERY_MAX_WAIT_SECONDS, retries=1)[0]

    def _format(self, text: str, task: str, title: str | None) -> str:
        if self._task_type_model:
            return text
        if task == "RETRIEVAL_QUERY":
            return f"task: search result | query: {text}"
        return f"title: {(title or 'none')[:200]} | text: {text}"

    def _batch(self, texts: list[str], task: str, title: str | None, *, max_wait: float, retries: int) -> list[list[float]]:
        requests = []
        for text in texts:
            req: dict = {"model": f"models/{self.model}", "content": {"parts": [{"text": self._format(text, task, title)}]},
                         "outputDimensionality": self.dimensions}
            if self._task_type_model:
                req["taskType"] = task
                if title and task == "RETRIEVAL_DOCUMENT":
                    req["title"] = title[:200]
            requests.append(req)
        resp = self._post({"requests": requests}, max_wait=max_wait, retries=retries)
        try:
            vectors = [e["values"] for e in resp.json()["embeddings"]]
        except (ValueError, KeyError, TypeError) as exc:
            raise EmbeddingError("The embedding service returned an invalid response.") from exc
        if len(vectors) != len(texts):
            raise EmbeddingError(f"Expected {len(texts)} embeddings, got {len(vectors)}.")
        for v in vectors:
            if len(v) != self.dimensions or not all(isinstance(x, int | float) for x in v):
                raise EmbeddingError(
                    f"Embedding dimension mismatch: the model returned {len(v)} values, the index stores {self.dimensions}.",
                    code="EMBEDDING_DIMENSION_MISMATCH")
        return vectors

    def _post(self, body: dict, *, max_wait: float, retries: int) -> httpx.Response:
        for attempt in range(retries + 1):
            try:
                with httpx.Client(timeout=self._timeout, transport=self._transport) as client:
                    resp = client.post(self._url, json=body, headers={"x-goog-api-key": self._key})
            except httpx.HTTPError as exc:
                logger.warning("Embedding service unreachable", extra={"error": type(exc).__name__})
                raise EmbeddingError("The embedding service is unreachable.") from exc
            if resp.status_code == 200:
                return resp
            if resp.status_code in (429, 503) and attempt < retries:
                match = _RETRY_DELAY.search(resp.text)
                wait = float(match.group(1)) + 1 if match else 2.0 * (attempt + 1)
                if wait <= max_wait:
                    logger.info("Embedding rate limited; waiting", extra={"seconds": round(wait, 1)})
                    self._sleep(wait)
                    continue
            # Log the status only: the error body can echo request content.
            logger.warning("Embedding request failed", extra={"status": resp.status_code, "model": self.model})
            if resp.status_code == 429:
                raise EmbeddingRateLimited("The embedding quota is exhausted for now. Try again later.")
            if resp.status_code in (400, 404) and "API key" not in resp.text:
                raise EmbeddingError(f"The embedding model '{self.model}' rejected the request (HTTP {resp.status_code}).")
            if resp.status_code in (401, 403) or "API key" in resp.text:
                raise EmbeddingNotConfigured("The embedding API key was rejected.")
            raise EmbeddingError(f"The embedding service failed (HTTP {resp.status_code}).")
        raise EmbeddingError("The embedding service failed.")  # pragma: no cover

    @staticmethod
    def _sleep(seconds: float) -> None:
        time.sleep(seconds)


def get_embedding_provider() -> EmbeddingProvider:
    settings = get_settings()
    if not settings.embeddings_configured:
        raise EmbeddingNotConfigured(
            "Document search is not configured: set EMBEDDING_PROVIDER, EMBEDDING_API_KEY and EMBEDDING_MODEL.")
    return GeminiEmbeddingProvider(settings)
