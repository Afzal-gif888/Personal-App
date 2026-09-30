"""Document search (RAG): chunking, embeddings, pgvector storage, search, isolation, deletion.

Vector-search tests need PostgreSQL + pgvector (TEST_DATABASE_URL); they're skipped on SQLite.
Embeddings come from the test-only FakeEmbeddingProvider, except the opt-in live Gemini test.
"""

import json
import os
import uuid

import httpx
import pytest
from sqlalchemy import select, text

from app.core.config import get_settings
from app.jobs import scheduler
from app.models import Document, DocumentChunk
from app.models.enums import DocumentIndexStatus
from app.rag import indexing
from app.rag.chunking import ExtractionError, Page, chunk_pages, extract_pages, split_text
from app.rag.embeddings import (
    EmbeddingError,
    EmbeddingNotConfigured,
    EmbeddingRateLimited,
    GeminiEmbeddingProvider,
)
from tests.conftest import SessionLocal, requires_pgvector
from tests.fake_embeddings import make_pdf

ML_PAGES = [
    "Machine learning basics. A model learns patterns from training data.",
    "High variance can cause a machine learning model to overfit the training data. Regularization reduces overfitting.",
    "Cross validation estimates how well a model generalises to unseen data.",
]
DBMS_PAGES = ["Normalization removes redundancy in relational tables. Third normal form removes transitive dependency."]


def _upload(client, headers, name, pages):
    resp = client.post("/api/v1/documents", headers=headers, files={"file": (name, make_pdf(pages), "application/pdf")})
    assert resp.status_code == 201, resp.text
    return client.get(f"/api/v1/documents/{resp.json()['id']}", headers=headers).json()  # after background indexing


def _search(client, headers, query, **extra):
    return client.post("/api/v1/documents/search", headers=headers, json={"query": query, **extra})


@pytest.fixture
def loose(monkeypatch):
    """The fake embedder's scores are bag-of-words overlaps, lower than Gemini's."""
    monkeypatch.setattr(get_settings(), "document_search_min_similarity", 0.2)


# --- chunking -------------------------------------------------------------------------------------


def test_chunking_is_deterministic_and_keeps_pages():
    pages = [Page(1, "First page.\n\n" + "word " * 400), Page(2, "Second page text.")]
    a = chunk_pages(pages, max_chars=600, overlap=100)
    b = chunk_pages(pages, max_chars=600, overlap=100)
    assert a == b and [c.index for c in a] == list(range(len(a)))
    assert all(len(c.content) <= 600 for c in a)
    assert {c.page_number for c in a} == {1, 2} and a[-1].content == "Second page text."
    assert a[0].content_hash == b[0].content_hash and len(a[0].content_hash) == 64


def test_chunking_empty_and_whitespace_documents():
    assert chunk_pages([Page(1, ""), Page(2, "   \n\n \x00 ")], max_chars=600, overlap=100) == []
    assert split_text("", max_chars=600, overlap=100) == []


def test_extract_pdf_pages_and_malformed_pdf(tmp_path):
    good = tmp_path / "ml.pdf"
    good.write_bytes(make_pdf(ML_PAGES))
    pages = extract_pages(good, "application/pdf")
    assert [p.number for p in pages] == [1, 2, 3] and "overfit" in pages[1].text
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"%PDF-1.4 this is not really a pdf")
    with pytest.raises(ExtractionError):
        extract_pages(bad, "application/pdf")


# --- Gemini embedding provider (HTTP mocked) -------------------------------------------------------


def _gemini(handler, dims=768, model="gemini-embedding-2"):
    s = get_settings().model_copy(update={"embedding_model": model, "embedding_api_key": "k-test", "embedding_dimensions": dims})
    provider = GeminiEmbeddingProvider(s, transport=httpx.MockTransport(handler))
    provider._sleep = lambda seconds: None  # type: ignore[method-assign]
    return provider


def test_gemini_provider_request_format_and_batching():
    seen = []

    def handler(request: httpx.Request):
        body = json.loads(request.content)
        seen.append((request.headers["x-goog-api-key"], request.url.path, body))
        return httpx.Response(200, json={"embeddings": [{"values": [0.1] * 768} for _ in body["requests"]]})

    p = _gemini(handler)
    vectors = p.embed_documents([f"passage {i}" for i in range(150)], title="ML_Notes.pdf")
    assert len(vectors) == 150 and all(len(v) == 768 for v in vectors)
    assert [len(b["requests"]) for _, _, b in seen] == [100, 50]  # batched at the API limit
    key, path, body = seen[0]
    assert key == "k-test" and path.endswith("/models/gemini-embedding-2:batchEmbedContents")
    first = body["requests"][0]
    assert first["outputDimensionality"] == 768 and "taskType" not in first
    assert first["content"]["parts"][0]["text"] == "title: ML_Notes.pdf | text: passage 0"
    p.embed_query("What causes overfitting?")
    assert seen[-1][2]["requests"][0]["content"]["parts"][0]["text"] == "task: search result | query: What causes overfitting?"


def test_gemini_embedding_001_uses_task_types():
    seen = []

    def handler(request):
        seen.append(json.loads(request.content)["requests"][0])
        return httpx.Response(200, json={"embeddings": [{"values": [0.1] * 768}]})

    _gemini(handler, model="gemini-embedding-001").embed_query("overfitting")
    assert seen[0]["taskType"] == "RETRIEVAL_QUERY" and seen[0]["content"]["parts"][0]["text"] == "overfitting"


def test_gemini_dimension_mismatch_and_invalid_response():
    wrong_dims = _gemini(lambda r: httpx.Response(200, json={"embeddings": [{"values": [0.1] * 3072}]}))
    with pytest.raises(EmbeddingError) as exc:
        wrong_dims.embed_query("x")
    assert exc.value.code == "EMBEDDING_DIMENSION_MISMATCH"
    garbage = _gemini(lambda r: httpx.Response(200, json={"unexpected": True}))
    with pytest.raises(EmbeddingError, match="invalid response"):
        garbage.embed_query("x")
    too_few = _gemini(lambda r: httpx.Response(200, json={"embeddings": []}))
    with pytest.raises(EmbeddingError, match="Expected 1 embeddings"):
        too_few.embed_query("x")


def test_gemini_api_failures():
    calls = {"n": 0}

    def quota(request):
        calls["n"] += 1
        return httpx.Response(429, json={"error": {"details": [{"retryDelay": "1s"}]}})

    with pytest.raises(EmbeddingRateLimited):
        _gemini(quota).embed_documents(["a"])
    assert calls["n"] == 4  # indexing waits and retries 3 times before giving up
    with pytest.raises(EmbeddingNotConfigured):
        _gemini(lambda r: httpx.Response(403, json={"error": {"message": "API key not valid"}})).embed_query("x")
    with pytest.raises(EmbeddingError, match="HTTP 500"):
        _gemini(lambda r: httpx.Response(500, text="boom")).embed_query("x")

    def unreachable(request):
        raise httpx.ConnectError("down")

    with pytest.raises(EmbeddingError, match="unreachable"):
        _gemini(unreachable).embed_query("x")


def test_embeddings_not_configured_is_explicit(monkeypatch):
    from app.rag.embeddings import get_embedding_provider

    monkeypatch.setattr(get_settings(), "embedding_api_key", "")
    with pytest.raises(EmbeddingNotConfigured):
        get_embedding_provider()


# --- indexing (upload -> chunks -> embeddings -> rows) ---------------------------------------------


def test_upload_indexes_once_with_pages_and_metadata(client, auth, embeddings):
    doc = _upload(client, auth, "ML_Notes.pdf", ML_PAGES)
    assert doc["indexStatus"] == "indexed" and doc["chunkCount"] == 3 and doc["indexedAt"]
    assert embeddings.document_calls == 1 and embeddings.embedded_texts == 3
    with SessionLocal() as db:
        chunks = db.scalars(select(DocumentChunk).order_by(DocumentChunk.chunk_index)).all()
        assert [c.page_number for c in chunks] == [1, 2, 3]
        assert all(len(list(c.embedding)) == 768 for c in chunks)
        assert chunks[1].meta == {"filename": "ML_Notes.pdf", "page": 2, "mimeType": "application/pdf"}
        assert str(chunks[0].document_id) == doc["id"] and chunks[0].character_count == len(chunks[0].content)


def test_reindexing_unchanged_document_reuses_embeddings_and_never_duplicates(client, auth, embeddings):
    doc = _upload(client, auth, "ML_Notes.pdf", ML_PAGES)
    for _ in range(2):
        resp = client.post(f"/api/v1/documents/{doc['id']}/reindex", headers=auth)
        assert resp.status_code == 200
    assert embeddings.document_calls == 1  # same text + model: no new embedding calls
    with SessionLocal() as db:
        assert db.scalar(select(DocumentChunk.id).where(DocumentChunk.chunk_index == 0)) is not None
        assert len(db.scalars(select(DocumentChunk)).all()) == 3


def test_model_change_triggers_reindex_from_scheduler(client, auth, embeddings):
    _upload(client, auth, "ML_Notes.pdf", ML_PAGES)
    embeddings.model = "fake-embedding-v2"
    assert scheduler.run_once()["documents_indexed"] == 1
    assert embeddings.document_calls == 2
    with SessionLocal() as db:
        assert db.scalar(select(Document.embedding_model)) == "fake-embedding-v2"
        assert len(db.scalars(select(DocumentChunk)).all()) == 3


def test_non_text_and_empty_documents_are_marked_unsupported(client, auth):
    png = client.post("/api/v1/documents", headers=auth, files={"file": ("photo.png", b"\x89PNG\r\n\x1a\n" + b"0" * 64, "image/png")})
    blank = client.post("/api/v1/documents", headers=auth, files={"file": ("blank.txt", b"   \n\n  ", "text/plain")})
    for resp in (png, blank):
        doc = client.get(f"/api/v1/documents/{resp.json()['id']}", headers=auth).json()
        assert doc["indexStatus"] == "unsupported" and doc["indexError"]


def test_embedding_failure_is_recorded_then_retried(client, auth, embeddings, monkeypatch):
    def fail(texts, *, title=None):
        raise EmbeddingRateLimited("The embedding quota is exhausted for now. Try again later.")

    monkeypatch.setattr(embeddings, "embed_documents", fail)
    doc = _upload(client, auth, "ML_Notes.pdf", ML_PAGES)
    assert doc["indexStatus"] == "failed" and "quota" in doc["indexError"] and doc["chunkCount"] == 0
    monkeypatch.undo()
    monkeypatch.setattr("app.rag.indexing.get_embedding_provider", lambda: embeddings)
    retried = client.post(f"/api/v1/documents/{doc['id']}/reindex", headers=auth)
    assert retried.status_code == 200
    assert client.get(f"/api/v1/documents/{doc['id']}", headers=auth).json()["indexStatus"] == "indexed"


def test_malformed_pdf_fails_without_retries(client, auth):
    resp = client.post("/api/v1/documents", headers=auth, files={"file": ("bad.pdf", b"%PDF-1.4 garbage", "application/pdf")})
    doc = client.get(f"/api/v1/documents/{resp.json()['id']}", headers=auth).json()
    assert doc["status"] == "failed"  # the upload itself is unreadable, so it is never indexed
    with SessionLocal() as db:
        assert db.get_one(Document, uuid.UUID(doc["id"])).index_status == DocumentIndexStatus.PENDING
    assert indexing.index_document(uuid.UUID(doc["id"])) is None


# --- search (PostgreSQL + pgvector) ------------------------------------------------------------------


@requires_pgvector
def test_search_returns_relevant_chunk_with_source(client, auth, loose, embeddings):
    _upload(client, auth, "ML_Notes.pdf", ML_PAGES)
    _upload(client, auth, "DBMS_Notes.pdf", DBMS_PAGES)
    calls_before = embeddings.document_calls
    resp = _search(client, auth, "What causes overfitting?", topK=2)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    top = body["results"][0]
    assert top["documentName"] == "ML_Notes.pdf" and top["pageNumber"] == 2 and "overfit" in top["content"]
    assert 0 < top["similarity"] <= 1 and body["message"] is None and len(body["results"]) <= 2
    assert embeddings.document_calls == calls_before and embeddings.query_calls == 1  # only the query is embedded

    dbms = _search(client, auth, "What do my DBMS notes say about normalization?").json()["results"]
    assert dbms[0]["documentName"] == "DBMS_Notes.pdf"


@requires_pgvector
def test_search_top_k_and_document_filter(client, auth, loose):
    ml = _upload(client, auth, "ML_Notes.pdf", ML_PAGES)
    _upload(client, auth, "DBMS_Notes.pdf", DBMS_PAGES)
    only_ml = _search(client, auth, "model data normalization", documentIds=[ml["id"]]).json()["results"]
    assert only_ml and {r["documentName"] for r in only_ml} == {"ML_Notes.pdf"}
    assert len(_search(client, auth, "model data", topK=1).json()["results"]) == 1


@requires_pgvector
def test_no_relevant_content(client, auth):
    _upload(client, auth, "ML_Notes.pdf", ML_PAGES)
    body = _search(client, auth, "quantum computing qubits").json()
    assert body["results"] == [] and body["message"] == "No relevant document content found."


@requires_pgvector
def test_users_never_see_each_others_chunks(client, auth, other_auth, loose):
    a_doc = _upload(client, auth, "ML_Notes.pdf", ML_PAGES)
    assert _search(client, auth, "overfitting variance").json()["results"]
    as_b = _search(client, other_auth, "overfitting variance").json()
    assert as_b["results"] == [] and as_b["message"]
    # Naming A's document explicitly doesn't help either.
    assert _search(client, other_auth, "overfitting variance", documentIds=[a_doc["id"]]).json()["results"] == []
    # A user_id in the body is not accepted at all.
    forged = _search(client, other_auth, "overfitting", userId=str(uuid.uuid4()))
    assert forged.status_code == 422


@requires_pgvector
def test_deleting_a_document_removes_its_chunks_from_search(client, auth, loose):
    doc = _upload(client, auth, "ML_Notes.pdf", ML_PAGES)
    assert _search(client, auth, "overfitting variance").json()["results"]
    assert client.delete(f"/api/v1/documents/{doc['id']}", headers=auth).status_code == 204
    with SessionLocal() as db:
        assert db.scalars(select(DocumentChunk)).all() == []
    assert _search(client, auth, "overfitting variance").json()["results"] == []


@requires_pgvector
def test_vector_column_and_index_in_postgres(db):
    col = db.execute(text(
        "select format_type(a.atttypid, a.atttypmod) from pg_attribute a "
        "where a.attrelid = 'document_chunks'::regclass and a.attname = 'embedding'")).scalar()
    assert col == "vector(768)"
    indexdef = db.execute(text("select indexdef from pg_indexes where indexname = 'ix_document_chunks_embedding_hnsw'")).scalar()
    assert "hnsw" in indexdef and "vector_cosine_ops" in indexdef
    fks = {r[0] for r in db.execute(text(
        "select confrelid::regclass::text from pg_constraint where conrelid = 'document_chunks'::regclass and contype = 'f'"))}
    assert fks == {"documents", "users"}


def test_search_requires_auth_and_postgres(client, auth):
    assert client.post("/api/v1/documents/search", json={"query": "overfitting"}).status_code == 401
    if not os.environ.get("TEST_DATABASE_URL"):
        resp = _search(client, auth, "overfitting")
        assert resp.status_code == 503 and resp.json()["error"]["code"] == "DOCUMENT_SEARCH_UNAVAILABLE"


@requires_pgvector
def test_search_unavailable_when_not_configured(client, auth, monkeypatch):
    def not_configured():
        raise EmbeddingNotConfigured("Document search is not configured.")

    monkeypatch.setattr("app.rag.indexing.get_embedding_provider", not_configured)
    resp = _search(client, auth, "overfitting")
    assert resp.status_code == 503 and resp.json()["error"]["code"] == "DOCUMENT_SEARCH_UNAVAILABLE"


# --- live Gemini (opt-in: RUN_LIVE_EMBEDDING_TESTS=1, spends a few embedding requests) ----------------


@pytest.mark.skipif(not os.environ.get("RUN_LIVE_EMBEDDING_TESTS"), reason="calls the real Gemini API")
def test_live_gemini_semantic_search():
    from dotenv import dotenv_values

    env = dotenv_values(".env")
    s = get_settings().model_copy(update={"embedding_api_key": env["EMBEDDING_API_KEY"], "embedding_model": env["EMBEDDING_MODEL"]})
    p = GeminiEmbeddingProvider(s)
    docs = p.embed_documents(["High variance can cause a machine learning model to overfit the training data.",
                              "A relation is in third normal form when non-key attributes depend only on the key."])

    def cos(a, b):
        return sum(x * y for x, y in zip(a, b, strict=True)) / (sum(x * x for x in a) * sum(y * y for y in b)) ** 0.5

    overfit, quantum = p.embed_query("What causes overfitting?"), p.embed_query("What does my document say about quantum computing?")
    threshold = s.document_search_min_similarity
    assert cos(overfit, docs[0]) >= threshold > cos(overfit, docs[1])  # different words, same meaning
    assert max(cos(quantum, d) for d in docs) < threshold
