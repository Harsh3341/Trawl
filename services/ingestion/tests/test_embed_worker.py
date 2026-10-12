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


from app.events import TOPIC_DOCUMENT_INGESTED_DLQ


class BoomEmbedding:
    def embed(self, texts): raise RuntimeError("embedding down")


class FlakyEmbedding:
    def __init__(self, fails): self.fails = fails; self.calls = 0
    def embed(self, texts):
        self.calls += 1
        if self.calls <= self.fails:
            raise RuntimeError("transient")
        return [[0.02] * 768 for _ in texts]


def test_worker_routes_permanent_failures_to_dlq(db):
    broker = InMemoryBroker()
    doc_id = _seed(db, broker, url="https://x/2", h="h2")
    consumer = broker.consumer([TOPIC_DOCUMENT_INGESTED])
    n = run_once(consumer, db=db, embedding=BoomEmbedding(), producer=broker,
                 cfg=WorkerConfig(max_retries=3, retry_base_seconds=0))
    assert n == 1                                   # offset committed, stream not stalled
    assert db.document_status(doc_id) == "failed"
    assert db.count_chunks(doc_id) == 0
    dlq = broker.topics[TOPIC_DOCUMENT_INGESTED_DLQ]
    assert len(dlq) == 1 and dlq[0].value["documentId"] == doc_id
    assert TOPIC_CHUNK_EMBEDDED not in broker.topics  # never claimed success


def test_worker_retries_then_succeeds(db):
    broker = InMemoryBroker()
    doc_id = _seed(db, broker, url="https://x/3", h="h3")
    consumer = broker.consumer([TOPIC_DOCUMENT_INGESTED])
    run_once(consumer, db=db, embedding=FlakyEmbedding(fails=2), producer=broker,
             cfg=WorkerConfig(max_retries=3, retry_base_seconds=0))
    assert db.document_status(doc_id) == "embedded"
    assert broker.topics.get(TOPIC_DOCUMENT_INGESTED_DLQ, []) == []
    assert len(broker.topics[TOPIC_CHUNK_EMBEDDED]) == 1
