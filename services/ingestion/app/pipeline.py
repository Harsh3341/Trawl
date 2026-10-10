from __future__ import annotations
import argparse, hashlib, os
from dataclasses import dataclass
from app.chunker import chunk_text
from app.db import Database, StoredChunk


@dataclass(frozen=True)
class IngestResult:
    docs_ingested: int
    chunks_written: int


def ingest_repo(repo: str, *, github, db, embedding, max_words: int = 200, overlap: int = 30) -> IngestResult:
    seed_url = f"https://github.com/{repo}"
    source_id = db.ensure_source(repo, "github_release", seed_url)
    docs = chunks_total = 0
    for rel in github.fetch_releases(repo):
        content_hash = hashlib.sha256(rel.body.encode()).hexdigest()
        doc_id, changed = db.upsert_document(
            source_id, rel.url, rel.title, rel.version, rel.body, content_hash)
        if not changed:
            continue
        pieces = chunk_text(rel.body, max_words=max_words, overlap=overlap)
        if not pieces:
            continue
        vectors = embedding.embed([p.text for p in pieces])
        db.replace_chunks(doc_id, [
            StoredChunk(p.ordinal, p.text, p.token_count, v) for p, v in zip(pieces, vectors)])
        docs += 1
        chunks_total += len(pieces)
    return IngestResult(docs_ingested=docs, chunks_written=chunks_total)


def main() -> None:
    from app.github import GitHubReleaseClient
    from app.embedding_client import EmbeddingClient
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", help="owner/name, e.g. acme/widget")
    repo = parser.parse_args().repo
    db = Database.connect(os.environ["DATABASE_URL"])
    res = ingest_repo(repo, github=GitHubReleaseClient(), db=db, embedding=EmbeddingClient())
    print(f"ingested {res.docs_ingested} docs, {res.chunks_written} chunks")


if __name__ == "__main__":
    main()
