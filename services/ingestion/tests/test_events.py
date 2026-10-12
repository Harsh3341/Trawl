from dataclasses import asdict
from app.events import (
    DocumentIngested, ChunkEmbedded, InMemoryBroker, now_ts,
    TOPIC_DOCUMENT_INGESTED,
)


def test_document_ingested_serializes_to_wire_shape():
    evt = DocumentIngested(documentId=7, sourceId=3, url="https://x/7",
                           contentHash="abc", ts=now_ts())
    assert asdict(evt) == {
        "documentId": 7, "sourceId": 3, "url": "https://x/7",
        "contentHash": "abc", "ts": evt.ts,
    }


def test_in_memory_broker_round_trips_in_order():
    broker = InMemoryBroker()
    broker.produce(TOPIC_DOCUMENT_INGESTED, key="7", value={"documentId": 7})
    broker.produce(TOPIC_DOCUMENT_INGESTED, key="8", value={"documentId": 8})
    consumer = broker.consumer([TOPIC_DOCUMENT_INGESTED])
    first, second = consumer.poll(), consumer.poll()
    assert first.value["documentId"] == 7 and first.key == "7"
    assert second.value["documentId"] == 8
    assert consumer.poll() is None  # drained
