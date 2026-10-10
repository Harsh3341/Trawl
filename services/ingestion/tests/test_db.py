from app.db import StoredChunk


def test_upsert_document_reports_change(db):
    sid = db.ensure_source("acme/widget", "github_release", "https://github.com/acme/widget")
    doc_id, changed = db.upsert_document(sid, "https://x/1", "v2", "v2", "body one", "hash1")
    assert changed is True
    same_id, changed2 = db.upsert_document(sid, "https://x/1", "v2", "v2", "body one", "hash1")
    assert same_id == doc_id and changed2 is False           # unchanged hash
    _, changed3 = db.upsert_document(sid, "https://x/1", "v2", "v2", "new body", "hash2")
    assert changed3 is True                                   # hash changed


def test_replace_chunks_sets_embedded(db):
    sid = db.ensure_source("acme/widget", "github_release", "https://github.com/acme/widget")
    doc_id, _ = db.upsert_document(sid, "https://x/2", "v1", "v1", "text", "h")
    db.replace_chunks(doc_id, [StoredChunk(0, "chunk a", 2, [0.1] * 768)])
    assert db.count_chunks(doc_id) == 1
    assert db.document_status(doc_id) == "embedded"
    db.replace_chunks(doc_id, [StoredChunk(0, "c0", 1, [0.0]*768), StoredChunk(1, "c1", 1, [0.0]*768)])
    assert db.count_chunks(doc_id) == 2                        # replaced, not appended
