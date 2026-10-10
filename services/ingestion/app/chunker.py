from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    ordinal: int
    text: str
    token_count: int


def chunk_text(text: str, max_words: int = 200, overlap: int = 30) -> list[Chunk]:
    assert 0 <= overlap < max_words, "overlap must be < max_words"
    words = text.split()
    if not words:
        return []
    step = max_words - overlap
    chunks: list[Chunk] = []
    for ordinal, start in enumerate(range(0, len(words), step)):
        window = words[start:start + max_words]
        chunks.append(Chunk(ordinal=ordinal, text=" ".join(window), token_count=len(window)))
        if start + max_words >= len(words):
            break
    return chunks
