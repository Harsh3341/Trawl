from dataclasses import asdict
from app.embed_worker import run_once, WorkerConfig
from app.events import (DocumentIngested, InMemoryBroker, now_ts,
                        TOPIC_DOCUMENT_INGESTED, TOPIC_CHUNK_EMBEDDED)


class FakeEmbedding:
    def embed(self, texts): return [[0.01 * (i + 1)] * 768 for i, _ in enumerate(texts)]


def _seed(db, broker, url="https://x/1", body="Added dark mode. Fixed a bug.", h="h1"):
    sid = db.ensure_source("acme/widget", "github_release", "https://github.com/acme/widget")
    doc_id, _ = db.upsert_document(sid, url, "v2", "v2", body, h)
    broker.produce(TOPIC_DOCUMENT_INGESTED, key=str(doc_id),
                   value=asdict(DocumentIngested(doc_id, sid, url, h, now_ts())))
    return doc_id


def test_worker_embeds_stores_and_publishes(db):
    broker = InMemoryBroker()
    doc_id = _seed(db, broker)
    consumer = broker.consumer([TOPIC_DOCUMENT_INGESTED])
    n = run_once(consumer, db=db, embedding=FakeEmbedding(), producer=broker,
                 cfg=WorkerConfig(retry_base_seconds=0))
    assert n == 1
    assert db.document_status(doc_id) == "embedded"
    assert db.count_chunks(doc_id) >= 1
    emitted = broker.topics[TOPIC_CHUNK_EMBEDDED]
    assert len(emitted) == 1
    assert emitted[0].value["documentId"] == doc_id
    assert emitted[0].value["chunkCount"] == db.count_chunks(doc_id)
