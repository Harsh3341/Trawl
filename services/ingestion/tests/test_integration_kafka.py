import time, uuid, pytest

pytest.importorskip("confluent_kafka")

from app.kafka_io import KafkaProducer, KafkaConsumer, create_topics, bootstrap_servers
from app.events import ALL_TOPICS, TOPIC_DOCUMENT_INGESTED
from app.crawler import crawl_repo
from app.embed_worker import handle, WorkerConfig
from app.github import Release


class FakeGitHub:
    def __init__(self, releases): self._r = releases
    def fetch_releases(self, repo): return self._r


class FakeEmbedding:
    def embed(self, texts): return [[0.03] * 768 for _ in texts]


def _broker_up() -> bool:
    from confluent_kafka.admin import AdminClient
    try:
        AdminClient({"bootstrap.servers": bootstrap_servers()}).list_topics(timeout=3)
        return True
    except Exception:
        return False


@pytest.mark.skipif(not _broker_up(), reason="no Kafka broker reachable")
def test_crawler_to_worker_through_real_kafka(db):
    create_topics(ALL_TOPICS)
    url = f"https://x/{uuid.uuid4()}"
    producer = KafkaProducer()
    crawl_repo("acme/widget", db=db, producer=producer,
               github=FakeGitHub([Release(url, "v1", "v1", "Added dark mode. Fixed a bug.")]))

    consumer = KafkaConsumer([TOPIC_DOCUMENT_INGESTED], group_id=f"test-{uuid.uuid4()}")
    cfg = WorkerConfig(retry_base_seconds=0)
    target, deadline = None, time.time() + 20
    while time.time() < deadline and target is None:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        handle(msg, db=db, embedding=FakeEmbedding(), producer=producer, cfg=cfg)
        consumer.commit()
        if msg.value.get("url") == url:
            target = int(msg.value["documentId"])
    consumer.close()

    assert target is not None, "crawled document never observed on the topic"
    assert db.document_status(target) == "embedded"
    assert db.count_chunks(target) >= 1
