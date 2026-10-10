import respx, httpx
from app.embedding_client import EmbeddingClient


@respx.mock
def test_embed_posts_texts_and_returns_vectors():
    route = respx.post("http://emb:8000/embed").mock(
        return_value=httpx.Response(200, json={"vectors": [[0.1]*768, [0.2]*768], "dim": 768}))
    vecs = EmbeddingClient("http://emb:8000").embed(["a", "b"])
    assert len(vecs) == 2 and len(vecs[0]) == 768
    assert route.calls.last.request.content  # body was sent
