# Insight Pipeline

A data-ingestion and retrieval platform that crawls developer documentation and
GitHub release notes, structures and indexes the content, and answers
natural-language questions over it with cited sources.

## Why

Products that answer questions over external knowledge are only as good as the
pipeline feeding them. This project builds that pipeline end to end: reliable
crawling, structured storage, vector indexing, a secured retrieval API, and a
chat + analytics UI.

## Architecture (high level)

```
Sources ─▶ Crawler ─▶ (Kafka) ─▶ Embedding worker ─▶ Postgres + pgvector
                 │                                          ▲
                 └─▶ Analytics (ClickHouse)                 │ retrieve
                                                            │
                     Next.js UI ─▶ RAG API gateway ─▶ Provider proxy ─▶ LLM
```

| Component | Stack | Responsibility |
|-----------|-------|----------------|
| Crawler | Python | Fetch + parse sources into structured documents |
| Embedding worker | Python | Chunk + embed documents into vectors |
| RAG API gateway | .NET Core | Secured retrieval + answer orchestration (JWT/OAuth) |
| Provider proxy | .NET Core | Route LLM/embedding calls across providers with failover |
| Analytics | ClickHouse | Ingestion + query metrics |
| Frontend | Next.js | Chat UI + analytics dashboard |

## Status

Design complete. See `docs/specs/` for the current design. Implementation plan
pending.

## Development

The full stack runs locally via `docker compose` (added during implementation).
