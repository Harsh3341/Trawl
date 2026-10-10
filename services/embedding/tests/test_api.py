import os
os.environ["EMBEDDER"] = "hash"          # offline, deterministic
from fastapi.testclient import TestClient
from app.main import app
from app.embedder import DIM

client = TestClient(app)

def test_health():
    assert client.get("/health").json() == {"status": "ok"}

def test_embed_returns_vectors():
    r = client.post("/embed", json={"texts": ["hello", "world"]})
    assert r.status_code == 200
    body = r.json()
    assert body["dim"] == DIM
    assert len(body["vectors"]) == 2
    assert len(body["vectors"][0]) == DIM

def test_embed_rejects_empty():
    assert client.post("/embed", json={"texts": []}).status_code == 422
