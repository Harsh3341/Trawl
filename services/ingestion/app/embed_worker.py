from __future__ import annotations
import time
from dataclasses import dataclass, asdict
from app.chunker import chunk_text
from app.db import StoredChunk
from app.events import (ChunkEmbedded, Consumer, Producer, now_ts,
                        TOPIC_CHUNK_EMBEDDED, TOPIC_DOCUMENT_INGESTED_DLQ)


@dataclass(frozen=True)
class WorkerConfig:
    max_retries: int = 3
    retry_base_seconds: float = 0.5
    max_words: int = 200
    overlap: int = 30


def _embed_document(document_id: int, *, db, embedding, cfg: WorkerConfig) -> int:
    doc = db.fetch_document(document_id)
    if doc is None:
        raise ValueError(f"document {document_id} not found")
    pieces = chunk_text(doc.content_text, max_words=cfg.max_words, overlap=cfg.overlap)
    vectors = embedding.embed([p.text for p in pieces]) if pieces else []
    db.replace_chunks(document_id, [
        StoredChunk(p.ordinal, p.text, p.token_count, v)
        for p, v in zip(pieces, vectors)])
    return len(pieces)


def handle(msg, *, db, embedding, producer: Producer,
           cfg: WorkerConfig, sleep=time.sleep) -> None:
    document_id = int(msg.value["documentId"])
    attempt = 0
    while True:
        try:
            count = _embed_document(document_id, db=db, embedding=embedding, cfg=cfg)
            producer.produce(TOPIC_CHUNK_EMBEDDED, key=str(document_id),
                             value=asdict(ChunkEmbedded(document_id, count, now_ts())))
            producer.flush()
            return
        except Exception:
            attempt += 1
            if attempt >= cfg.max_retries:
                producer.produce(TOPIC_DOCUMENT_INGESTED_DLQ,
                                 key=str(document_id), value=msg.value)
                producer.flush()
                db.mark_failed(document_id)
                return
            sleep(cfg.retry_base_seconds * (2 ** (attempt - 1)))


def run_once(consumer: Consumer, *, db, embedding, producer: Producer,
             cfg: WorkerConfig) -> int:
    processed = 0
    while True:
        msg = consumer.poll(timeout=1.0)
        if msg is None:
            break
        handle(msg, db=db, embedding=embedding, producer=producer, cfg=cfg)
        consumer.commit()
        processed += 1
    return processed


def main() -> None:
    import os, signal, sys
    from app.db import Database
    from app.embedding_client import EmbeddingClient
    from app.kafka_io import KafkaProducer, KafkaConsumer, create_topics
    from app.events import ALL_TOPICS, TOPIC_DOCUMENT_INGESTED
    once = "--once" in sys.argv
    cfg = WorkerConfig(
        max_retries=int(os.getenv("EMBED_MAX_RETRIES", "3")),
        retry_base_seconds=float(os.getenv("EMBED_RETRY_BASE_SECONDS", "0.5")))
    create_topics(ALL_TOPICS)
    db = Database.connect(os.environ["DATABASE_URL"])
    embedding = EmbeddingClient()
    producer = KafkaProducer()
    consumer = KafkaConsumer([TOPIC_DOCUMENT_INGESTED])
    stop = {"flag": False}
    signal.signal(signal.SIGTERM, lambda *_: stop.__setitem__("flag", True))
    signal.signal(signal.SIGINT, lambda *_: stop.__setitem__("flag", True))
    try:
        if once:
            run_once(consumer, db=db, embedding=embedding, producer=producer, cfg=cfg)
            return
        while not stop["flag"]:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
            handle(msg, db=db, embedding=embedding, producer=producer, cfg=cfg)
            consumer.commit()
    finally:
        consumer.close()


if __name__ == "__main__":
    main()
