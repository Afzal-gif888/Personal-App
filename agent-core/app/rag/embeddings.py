"""Embedding providers.

`HashingEmbeddingProvider` is a deterministic, dependency-free embedder (feature hashing over word
unigrams and bigrams, L2-normalised). It needs no API key, gives stable results in tests and is
good enough for keyword-heavy study notes. A semantic model can replace it behind the same
interface without touching the retriever or the agent.
"""

import hashlib
import math
import re
from abc import ABC, abstractmethod

from app.config.settings import Settings

_WORD = re.compile(r"[a-z0-9]+")
_STOP = frozenset(
    "a an the and or of to in on for with is are was were be been it this that these those as at by "
    "from my your our me i you we what how why when which who explain according please tell about into "
    "can could would should do does did not no yes so if then than there their them they he she his her".split()
)


def tokenize(text: str) -> list[str]:
    words = [w for w in _WORD.findall(text.lower()) if w not in _STOP and len(w) > 1]
    # Light stemming so "normalization" and "normalize" share features.
    return [re.sub(r"(ization|isation|ations|ation|ings|ing|izes|ized|ize|ies|es|s)$", "", w) or w for w in words]


class EmbeddingProvider(ABC):
    name: str = "base"
    dimensions: int

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """One vector per input text."""


class HashingEmbeddingProvider(EmbeddingProvider):
    name = "hashing"

    def __init__(self, dimensions: int = 512) -> None:
        self.dimensions = dimensions

    def _bucket(self, feature: str) -> tuple[int, float]:
        digest = hashlib.blake2b(feature.encode(), digest_size=8).digest()
        value = int.from_bytes(digest, "big")
        return value % self.dimensions, 1.0 if value >> 63 else -1.0

    def _embed_one(self, text: str) -> list[float]:
        vec = [0.0] * self.dimensions
        tokens = tokenize(text)
        features = tokens + [f"{a}_{b}" for a, b in zip(tokens, tokens[1:], strict=False)]
        for feature in features:
            idx, sign = self._bucket(feature)
            vec[idx] += sign
        norm = math.sqrt(sum(v * v for v in vec))
        return [v / norm for v in vec] if norm else vec

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]


def create_embedding_provider(settings: Settings) -> EmbeddingProvider:
    # "" and "hashing" both mean the built-in embedder; other providers plug in here.
    return HashingEmbeddingProvider(settings.embedding_dimensions)
