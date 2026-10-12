from __future__ import annotations
import json, os
from app.events import Message


def bootstrap_servers(explicit: str | None = None) -> str:
    return explicit or os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:29092")


class KafkaProducer:
    def __init__(self, bootstrap: str | None = None) -> None:
        from confluent_kafka import Producer as _Producer  # lazy
        self._p = _Producer({"bootstrap.servers": bootstrap_servers(bootstrap)})

    def produce(self, topic: str, key: str, value: dict) -> None:
        self._p.produce(topic, key=key, value=json.dumps(value).encode())

    def flush(self) -> None:
        self._p.flush()


class KafkaConsumer:
    def __init__(self, topics: list[str], group_id: str = "embed-worker",
                 bootstrap: str | None = None) -> None:
        from confluent_kafka import Consumer as _Consumer  # lazy
        self._c = _Consumer({
            "bootstrap.servers": bootstrap_servers(bootstrap),
            "group.id": group_id,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        })
        self._c.subscribe(topics)

    def poll(self, timeout: float = 1.0) -> "Message | None":
        m = self._c.poll(timeout)
        if m is None:
            return None
        if m.error():
            raise RuntimeError(str(m.error()))
        key = m.key().decode() if m.key() is not None else ""
        return Message(m.topic(), key, json.loads(m.value().decode()))

    def commit(self) -> None:
        self._c.commit(asynchronous=False)

    def close(self) -> None:
        self._c.close()


def create_topics(topics: list[str], bootstrap: str | None = None,
                  partitions: int = 1, replication: int = 1) -> None:
    from confluent_kafka.admin import AdminClient, NewTopic  # lazy
    admin = AdminClient({"bootstrap.servers": bootstrap_servers(bootstrap)})
    existing = set(admin.list_topics(timeout=10).topics)
    pending = [NewTopic(t, partitions, replication) for t in topics if t not in existing]
    if not pending:
        return
    for _, fut in admin.create_topics(pending).items():
        fut.result()
