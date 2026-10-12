from __future__ import annotations
import hashlib
from dataclasses import dataclass, asdict
from app.events import DocumentIngested, Producer, TOPIC_DOCUMENT_INGESTED, now_ts


@dataclass(frozen=True)
class CrawlResult:
    documents_seen: int
    events_published: int


def crawl_repo(repo: str, *, github, db, producer: Producer) -> CrawlResult:
    seed_url = f"https://github.com/{repo}"
    source_id = db.ensure_source(repo, "github_release", seed_url)
    seen = published = 0
    for rel in github.fetch_releases(repo):
        seen += 1
        content_hash = hashlib.sha256(rel.body.encode()).hexdigest()
        doc_id, changed = db.upsert_document(
            source_id, rel.url, rel.title, rel.version, rel.body, content_hash)
        if not changed:
            continue
        evt = DocumentIngested(documentId=doc_id, sourceId=source_id,
                               url=rel.url, contentHash=content_hash, ts=now_ts())
        producer.produce(TOPIC_DOCUMENT_INGESTED, key=str(doc_id), value=asdict(evt))
        published += 1
    producer.flush()
    return CrawlResult(documents_seen=seen, events_published=published)


def main() -> None:
    import argparse, os
    from app.db import Database
    from app.github import GitHubReleaseClient
    from app.kafka_io import KafkaProducer, create_topics
    from app.events import ALL_TOPICS
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", help="owner/name, e.g. pallets/flask")
    repo = parser.parse_args().repo
    create_topics(ALL_TOPICS)
    db = Database.connect(os.environ["DATABASE_URL"])
    res = crawl_repo(repo, github=GitHubReleaseClient(), db=db, producer=KafkaProducer())
    print(f"crawled {res.documents_seen} docs, published {res.events_published} events")


if __name__ == "__main__":
    main()
