from app.github import Release
from app.pipeline import ingest_repo


class FakeGitHub:
    def __init__(self, releases): self._r = releases
    def fetch_releases(self, repo): return self._r


class FakeEmbedding:
    def embed(self, texts): return [[0.01 * (i + 1)] * 768 for i, _ in enumerate(texts)]


def _releases():
    return [Release("https://x/r1", "v2", "v2", "Added dark mode. Fixed a bug."),
            Release("https://x/r2", "v1", "v1", "Initial release.")]


def test_ingest_writes_docs_and_chunks(db):
    res = ingest_repo("acme/widget", github=FakeGitHub(_releases()),
                      db=db, embedding=FakeEmbedding())
    assert res.docs_ingested == 2
    assert res.chunks_written >= 2


def test_ingest_is_idempotent(db):
    args = dict(github=FakeGitHub(_releases()), db=db, embedding=FakeEmbedding())
    ingest_repo("acme/widget", **args)
    second = ingest_repo("acme/widget", **args)     # same hashes
    assert second.docs_ingested == 0                 # nothing re-embedded
