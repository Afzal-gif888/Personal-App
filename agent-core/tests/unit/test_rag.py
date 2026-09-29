import pytest

from app.rag.embeddings import HashingEmbeddingProvider
from app.rag.pipeline import DocumentIngestionPipeline, ExtractionError, chunk_text, extract_text
from app.rag.retriever import InMemoryVectorStore, Retriever, cosine
from tests.fakes import USER_A, USER_B

DBMS = """Normalization is the process of organising a relational database to reduce redundancy.
First normal form (1NF) requires atomic values in every column.

Second normal form (2NF) removes partial dependencies on a composite key.

Third normal form (3NF) removes transitive dependencies between non-key attributes."""

ML = """Gradient descent minimises a loss function by moving parameters against the gradient.
The learning rate controls the step size.

Overfitting happens when a model memorises the training data; regularisation helps."""


def pipeline(store=None, embedder=None):
    store = store or InMemoryVectorStore()
    embedder = embedder or HashingEmbeddingProvider(256)
    return DocumentIngestionPipeline(store, embedder, chunk_chars=300, overlap=60, max_bytes=1_000_000), store, embedder


def test_chunking_respects_size_and_overlap():
    text = "\n\n".join(f"Paragraph {i}. " + "word " * 40 for i in range(10))
    chunks = chunk_text(text, max_chars=300, overlap=60)
    assert len(chunks) > 3 and all(len(c) <= 300 for c in chunks)
    assert chunk_text("   ") == []
    long_para = "sentence. " * 200
    assert all(len(c) <= 300 for c in chunk_text(long_para, max_chars=300, overlap=50))


def test_extraction():
    assert extract_text(b"hello", "text/markdown; charset=utf-8") == "hello"
    with pytest.raises(ExtractionError):
        extract_text(b"x", "application/zip")
    with pytest.raises(ExtractionError):
        extract_text(b"not a pdf", "application/pdf")


async def test_embeddings_are_deterministic_and_normalised():
    e = HashingEmbeddingProvider(128)
    [a], [b] = await e.embed(["normalization of tables"]), await e.embed(["normalization of tables"])
    assert a == b and abs(cosine(a, a) - 1) < 1e-9
    [c] = await e.embed(["gradient descent learning rate"])
    assert cosine(a, c) < 0.3


async def test_retrieves_the_relevant_chunk():
    pipe, store, embedder = pipeline()
    await pipe.index_text(USER_A, "d1", "DBMS notes", DBMS)
    await pipe.index_text(USER_A, "d2", "ML notes", ML)
    hits = await Retriever(store, embedder, top_k=2, min_score=0.1).retrieve(USER_A, "explain normalization and normal forms")
    assert hits and hits[0].document_name == "DBMS notes" and "Normalization" in hits[0].text
    ml_hits = await Retriever(store, embedder, top_k=1, min_score=0.1).retrieve(USER_A, "what is gradient descent")
    assert ml_hits[0].document_name == "ML notes"


async def test_irrelevant_queries_return_nothing():
    pipe, store, embedder = pipeline()
    await pipe.index_text(USER_A, "d1", "DBMS notes", DBMS)
    assert await Retriever(store, embedder, min_score=0.15).retrieve(USER_A, "best pizza places in Bangalore") == []


async def test_users_never_see_each_others_chunks():
    pipe, store, embedder = pipeline()
    await pipe.index_text(USER_A, "d1", "DBMS notes", DBMS)
    assert await Retriever(store, embedder, min_score=0).retrieve(USER_B, "normalization") == []


async def test_reindexing_replaces_old_chunks():
    pipe, store, _ = pipeline()
    await pipe.index_text(USER_A, "d1", "notes", DBMS, version="1")
    first = store.chunk_count(USER_A)
    await pipe.index_text(USER_A, "d1", "notes", "short replacement text", version="2")
    assert store.chunk_count(USER_A) == 1 < first
    assert await store.document_version(USER_A, "d1") == "2"


async def test_ensure_indexed_uses_backend_and_skips_unchanged(harness):
    harness.fake.add_document(USER_A, "DBMS notes.txt", DBMS)
    harness.fake.add(USER_A, "documents", name="slides.pptx", mimeType="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                     size=10, category=None, status="ready", pageCount=None, processedAt=None)
    pipe = harness.services.rag.pipeline
    async with harness.client() as backend:
        first = await pipe.ensure_indexed(backend, USER_A)
        second = await pipe.ensure_indexed(backend, USER_A)
    assert len(first.indexed) == 1 and len(first.skipped) == 1
    assert second.indexed == [] and len(second.skipped) == 2
    downloads = [p for m, p in harness.fake.calls if p.endswith("/download")]
    assert len(downloads) == 1


async def test_meta_words_in_questions_do_not_dilute_matching():
    from app.rag.retriever import clean_query

    assert clean_query("According to my uploaded notes, explain normalization.") == "to my , normalization."
    assert clean_query("notes") == "notes"  # never reduced to an empty query
    pipe, store, embedder = pipeline()
    await pipe.index_text(USER_A, "d1", "DBMS notes", "Normalization organises tables to reduce redundancy.\n\nIndexes speed up lookups.")
    hits = await Retriever(store, embedder, min_score=0.12).retrieve(USER_A, "According to my uploaded notes, explain normalization.")
    assert hits and hits[0].document_id == "d1"
