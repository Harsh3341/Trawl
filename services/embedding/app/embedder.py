from __future__ import annotations
import hashlib
import os
from typing import Protocol

DIM = 768

class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...

class HashEmbedder:
    """Deterministic, offline, dependency-free. For tests and local dev."""
    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for t in texts:
            vec: list[float] = []
            counter = 0
            while len(vec) < DIM:
                h = hashlib.sha256(f"{counter}:{t}".encode()).digest()
                for b in h:
                    vec.append((b / 255.0) * 2.0 - 1.0)  # [-1, 1]
                    if len(vec) == DIM:
                        break
                counter += 1
            out.append(vec)
        return out

class SentenceTransformerEmbedder:
    """Real 768-dim model (all-mpnet-base-v2). Requires the [model] extra."""
    def __init__(self) -> None:
        from sentence_transformers import SentenceTransformer
        self._model = SentenceTransformer("all-mpnet-base-v2")

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [v.tolist() for v in self._model.encode(texts, normalize_embeddings=True)]

def get_embedder() -> Embedder:
    return HashEmbedder() if os.getenv("EMBEDDER") == "hash" else SentenceTransformerEmbedder()
