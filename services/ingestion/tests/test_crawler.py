from app.github import Release
from app.crawler import crawl_repo
from app.events import InMemoryBroker, TOPIC_DOCUMENT_INGESTED


class FakeGitHub:
    def __init__(self, releases): self._r = releases
    def fetch_releases(self, repo): return self._r


def _releases():
    return [Release("https://x/r1", "v2", "v2", "Added dark mode. Fixed a bug."),
            Release("https://x/r2", "v1", "v1", "Initial release.")]


def test_crawl_publishes_one_event_per_changed_document(db):
    broker = InMemoryBroker()
    res = crawl_repo("acme/widget", github=FakeGitHub(_releases()), db=db, producer=broker)
    assert res.events_published == 2
    msgs = broker.topics[TOPIC_DOCUMENT_INGESTED]
    assert len(msgs) == 2
    assert {m.value["url"] for m in msgs} == {"https://x/r1", "https://x/r2"}
    assert all(m.key == str(m.value["documentId"]) for m in msgs)
    assert all(m.value["contentHash"] for m in msgs)


def test_crawl_skips_unchanged_documents(db):
    crawl_repo("acme/widget", github=FakeGitHub(_releases()), db=db, producer=InMemoryBroker())
    broker2 = InMemoryBroker()
    res = crawl_repo("acme/widget", github=FakeGitHub(_releases()), db=db, producer=broker2)
    assert res.events_published == 0
    assert broker2.topics.get(TOPIC_DOCUMENT_INGESTED, []) == []
