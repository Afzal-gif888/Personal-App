"""TEST-ONLY embedding provider and PDF builder.

`FakeEmbeddingProvider` is a deterministic bag-of-words hasher so tests can exercise indexing,
storage, pgvector search, top_k, user isolation and deletion without calling Gemini. It is not
semantic and is never used outside tests; real semantic behaviour is checked against the Gemini
API in test_document_search.py::test_live_gemini_semantic_search (opt-in).
"""

import hashlib
import math
import re

from app.rag.embeddings import EmbeddingProvider

_WORD = re.compile(r"[a-z]+")
_STOP = {"the", "a", "an", "of", "to", "in", "and", "is", "what", "my", "does", "say", "about", "do", "notes", "can"}


class FakeEmbeddingProvider(EmbeddingProvider):
    name = "fake"

    def __init__(self, model: str = "fake-embedding", dimensions: int = 768) -> None:
        self.model = model
        self.dimensions = dimensions
        self.document_calls = 0
        self.query_calls = 0
        self.embedded_texts = 0

    def _vector(self, text: str) -> list[float]:
        vec = [0.0] * self.dimensions
        for word in _WORD.findall(text.lower()):
            if word in _STOP:
                continue
            word = word[:6]  # crude stemming: "overfitting" ~ "overfit"
            digest = int.from_bytes(hashlib.blake2b(word.encode(), digest_size=8).digest(), "big")
            vec[digest % self.dimensions] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        # Never all-zero: pgvector's cosine distance is undefined for a zero vector.
        return [v / norm for v in vec] if any(vec) else [1.0 / math.sqrt(self.dimensions)] * self.dimensions

    def embed_documents(self, texts: list[str], *, title: str | None = None) -> list[list[float]]:
        self.document_calls += 1
        self.embedded_texts += len(texts)
        return [self._vector(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        self.query_calls += 1
        return self._vector(text)


def make_pdf(pages: list[str]) -> bytes:
    """A real PDF with one text page per entry (Helvetica, one line per sentence)."""
    objects: list[bytes] = []
    kids = " ".join(f"{3 + i * 2} 0 R" for i in range(len(pages)))
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode())
    font_id = 3 + len(pages) * 2
    for i, text in enumerate(pages):
        lines = [s.strip() for s in text.split(". ") if s.strip()]
        ops = ["BT", "/F1 10 Tf", "40 750 Td", "12 TL"]
        for line in lines:
            safe = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            ops.append(f"({safe}) Tj T*")
        ops.append("ET")
        stream = "\n".join(ops).encode("latin-1")
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents {4 + i * 2} 0 R "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> >>".encode()
        )
        objects.append(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for n, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{n} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    out += b"".join(f"{o:010d} 00000 n \n".encode() for o in offsets)
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)
