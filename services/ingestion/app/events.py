from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

TOPIC_DOCUMENT_INGESTED = "document.ingested"
TOPIC_CHUNK_EMBEDDED = "chunk.embedded"
TOPIC_QUERY_ANSWERED = "query.answered"
TOPIC_DOCUMENT_INGESTED_DLQ = "document.ingested.dlq"

ALL_TOPICS = [
    TOPIC_DOCUMENT_INGESTED, TOPIC_CHUNK_EMBEDDED,
    TOPIC_QUERY_ANSWERED, TOPIC_DOCUMENT_INGESTED_DLQ,
]


def now_ts() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class DocumentIngested:
    documentId: int
    sourceId: int
    url: str
    contentHash: str
    ts: str


@dataclass(frozen=True)
class ChunkEmbedded:
    documentId: int
    chunkCount: int
    ts: str


@dataclass(frozen=True)
class Message:
    topic: str
    key: str
    value: dict


class Producer(Protocol):
    def produce(self, topic: str, key: str, value: dict) -> None: ...
    def flush(self) -> None: ...


class Consumer(Protocol):
    def poll(self, timeout: float = 1.0) -> "Message | None": ...
    def commit(self) -> None: ...
    def close(self) -> None: ...


class InMemoryBroker:
    """Deterministic in-process broker for hermetic unit tests."""

    def __init__(self) -> None:
        self.topics: dict[str, list[Message]] = {}

    def produce(self, topic: str, key: str, value: dict) -> None:
        self.topics.setdefault(topic, []).append(Message(topic, key, value))

    def flush(self) -> None:
        pass

    def consumer(self, topics: list[str]) -> "InMemoryConsumer":
        return InMemoryConsumer(self, topics)


class InMemoryConsumer:
    """Snapshots the broker's topics at creation and replays them once."""

    def __init__(self, broker: InMemoryBroker, topics: list[str]) -> None:
        self._queue: list[Message] = []
        for t in topics:
            self._queue.extend(broker.topics.get(t, []))
        self._pos = 0

    def poll(self, timeout: float = 1.0) -> "Message | None":
        if self._pos >= len(self._queue):
            return None
        msg = self._queue[self._pos]
        self._pos += 1
        return msg

    def commit(self) -> None:
        pass

    def close(self) -> None:
        pass
