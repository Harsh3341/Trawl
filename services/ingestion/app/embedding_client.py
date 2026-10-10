from __future__ import annotations
import os
import httpx


class EmbeddingClient:
    def __init__(self, base_url: str | None = None) -> None:
        self._base_url = (base_url or os.environ.get("EMBEDDING_URL", "http://localhost:8000")).rstrip("/")

    def embed(self, texts: list[str]) -> list[list[float]]:
        resp = httpx.post(f"{self._base_url}/embed", json={"texts": texts}, timeout=120)
        resp.raise_for_status()
        return resp.json()["vectors"]
