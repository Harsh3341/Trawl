from app.embedder import HashEmbedder, DIM

def test_hash_embedder_dim_and_determinism():
    e = HashEmbedder()
    v1 = e.embed(["hello world"])
    v2 = e.embed(["hello world"])
    assert len(v1) == 1 and len(v1[0]) == DIM
    assert v1 == v2                      # deterministic
    assert v1 != e.embed(["different"])  # content-sensitive

def test_hash_embedder_batch():
    out = HashEmbedder().embed(["a", "b", "c"])
    assert len(out) == 3 and all(len(v) == DIM for v in out)
