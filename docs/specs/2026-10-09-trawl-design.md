# Trawl — Design

Date: 2026-10-09
Status: Approved (pending implementation plan)

## 1. Overview

An AI-era data-ingestion and retrieval (RAG) system. It crawls external
developer documentation and GitHub release notes, structures and embeds the
content, and answers natural-language questions over it through a secured API
with a chat UI. It also exposes analytics on what was ingested and asked.

### Demo domain

Developer-tool documentation + GitHub release notes for a configured set of
projects. Example questions: "What changed in v5?", "How do I configure X?".

### Data flow

```
          ┌─ Crawler (Py) ────┐      ┌─ Embed worker (Py) ───┐
Sources ─▶│ fetch + parse     │─────▶│ chunk + embed         │
(docs,    │ (Playwright/HTTP) │ Kafka│ (sentence-transformers│
 GitHub)  └───────────────────┘ topic│  or provider API)     │
                │                     └───────────┬───────────┘
                │ raw+structured docs             │ vectors
                ▼                                 ▼
          Postgres (structured) ◀──────▶ Postgres + pgvector
                │                                 ▲
                │ crawl/query events (Kafka)      │ retrieve
                ▼                                 │
          ClickHouse (analytics)        ┌─────────┴──────────┐
                ▲                        │ .NET RAG gateway   │
                │ query logs             │ JWT/OAuth, retrieve│
                │                        │ + LLM proxy call   │
                │                        └─────────┬──────────┘
                │                                  │ answer
          Next.js UI  ◀───────────────────────────┘
          (chat + analytics dashboard)
```

### Build sequencing

Build a thin vertical slice first: one source → crawl → store → embed →
retrieve → one LLM call → UI shows the answer. Kafka, ClickHouse, the
multi-provider proxy, and the analytics dashboard are layered on once the
slice works end to end. No component is left half-finished.

## 2. Components, boundaries & interfaces

Each service owns one job and communicates through a defined contract, so the
services are independently buildable and testable.

1. **Crawler service (Python)**
   - Does: fetches a source, extracts clean text + metadata (url, title,
     version, source, fetched_at), splits into logical sections.
   - In: source config. Out: `RawDocument` rows in Postgres + a
     `document.ingested` Kafka event.
   - Honors robots.txt, rate limits, retries.

2. **Embedding worker (Python)**
   - Does: consumes `document.ingested`, chunks text, generates embeddings,
     upserts chunks + vectors.
   - In: Kafka event. Out: `Chunk` rows in pgvector + a `chunk.embedded` event.

3. **RAG API gateway (.NET Core)** — signature component
   - Does: secured front door. Validates JWT/OAuth, retrieves top-k chunks,
     builds a prompt, calls the LLM via the provider proxy, returns answer +
     citations. Emits `query.answered`.
   - In: `POST /ask { question }` (authed). Out: `{ answer, citations[],
     latencyMs }`.

4. **Provider proxy (.NET Core)** — reuse of the Forward Proxy pattern
   - Does: single internal interface for LLM/embedding calls; routes to a
     provider (Claude/OpenAI/local) with health checks + an enabled-provider
     whitelist and failover. Decouples the gateway from any one vendor.

5. **Analytics consumer + store (ClickHouse)**
   - Does: consumes `document.ingested` / `query.answered`, writes to
     ClickHouse for dashboards (docs/day, top questions, latency, hit rate).

6. **Frontend (Next.js)**
   - Does: chat UI (question → answer + citations) + analytics dashboard.
     Calls the gateway only; never touches the stores directly.

**Boundary rules:** services communicate via Kafka events (async) or the
gateway's REST contract (sync). Only the owning service writes to its store.
The UI talks to nothing but the gateway.

## 3. Data model & contracts

### Postgres — structured tables

```sql
sources(
  id, name, kind,                 -- kind: 'docs' | 'github_release'
  seed_url, crawl_rules jsonb,     -- allow/deny patterns, max_depth
  enabled bool, created_at
)

documents(
  id, source_id -> sources,
  url unique, title, version,     -- version nullable (e.g. 'v5.1.0')
  content_text,                   -- cleaned full text
  content_hash,                   -- dedup / change detection
  fetched_at, status              -- 'ingested'|'embedded'|'failed'
)

chunks(
  id, document_id -> documents,
  ordinal int,                    -- position within doc
  text,
  embedding vector(768),          -- pgvector; dim matches model
  token_count int
)
-- index: hnsw on chunks.embedding for ANN search
```

### ClickHouse — analytics (append-only)

```sql
ingest_events(ts, source_id, document_id, bytes, chunk_count, status)
query_events(ts, question, k, latency_ms, provider, retrieved_doc_ids Array, cited bool)
```

### Kafka topics & event shapes (JSON)

```jsonc
// topic: document.ingested
{ "documentId": "...", "sourceId": "...", "url": "...", "contentHash": "...", "ts": "..." }
// topic: chunk.embedded
{ "documentId": "...", "chunkCount": 12, "ts": "..." }
// topic: query.answered
{ "question": "...", "k": 5, "latencyMs": 740, "provider": "claude",
  "retrievedDocIds": ["..."], "cited": true, "ts": "..." }
```

### RAG gateway REST contract (.NET)

```jsonc
POST /ask            // requires: Authorization: Bearer <JWT>
  req:  { "question": "What changed in v5?", "k": 5 }
  resp: { "answer": "...",
          "citations": [ { "documentId": "...", "url": "...", "title": "...", "version": "v5.1.0" } ],
          "latencyMs": 740 }
GET  /sources        // list configured sources (authed)
POST /sources        // register a source to crawl (authed)
GET  /health         // liveness; includes provider-proxy health
```

### Provider proxy internal contract (.NET)

```jsonc
POST /internal/chat   { "messages": [...], "model": "..." } -> { "text": "...", "provider": "..." }
POST /internal/embed  { "texts": ["..."] }                  -> { "vectors": [[...]], "dim": 768 }
GET  /internal/providers   -> [ { "name": "claude", "healthy": true, "enabled": true } ]
```

Embedding dimension (768) must match the model. First slice uses a local
sentence-transformers model (`all-mpnet-base-v2`, 768-dim) so there is no API-key
dependency; the provider-API path is available later. Vector search uses pgvector
HNSW ANN.

## 4. Error handling, auth & testing

### Resilience

- **Crawler:** retry with exponential backoff; honor robots.txt + per-host rate
  limits; mark `documents.status='failed'` after N retries and continue (one bad
  page never stops a crawl). `content_hash` skips re-embedding unchanged pages.
- **Embedding worker:** commit Kafka offset only after a successful upsert;
  failed messages go to a `*.dlq` dead-letter topic.
- **RAG gateway:** if retrieval is empty, answer honestly ("no indexed docs
  cover this") rather than hallucinate; enforce a request timeout; structured
  error codes.
- **Provider proxy:** health-check providers; fail over to the next enabled
  provider if the primary is down; return 503 if all are down.

### Auth & security

- `/ask` and `/sources` require JWT/OAuth. Demo: a `/token` dev endpoint issues
  a signed JWT; design leaves room for a real OAuth provider.
- Secrets via environment / `.env`, never committed. The provider proxy is the
  only service holding LLM keys; the gateway and UI never see them.
- Input validation on `/ask` (length caps, sanitize). Internal proxy endpoints
  bound to the internal network, not public.
- **Prompt-injection risk:** the crawler ingests untrusted web content that can
  carry injection payloads into retrieved context. Mitigation: treat retrieved
  text as data, keep system instructions separate, and show citations so answers
  are auditable.

### Testing strategy

- **Unit:** crawler parser (HTML fixture → structured doc), chunker, provider
  routing/failover, JWT validation. Python via `pytest`; .NET via `xUnit`.
- **Integration:** crawl a local fixture site → Postgres; event flow through
  Kafka → embed worker → pgvector; `/ask` end to end against a seeded DB with a
  stubbed provider (deterministic, no real LLM calls in tests).
- **Contract:** assert `/ask` response + Kafka event shapes against §3 schemas.
- **Approach:** TDD — failing test first for each unit.
- Everything runs via `docker compose` locally; CI runs unit + integration
  against ephemeral containers.

## Open items for the implementation plan

- Concrete initial source list (which docs sites / repos).
- Chunking parameters (size, overlap).
- Local model download + caching strategy for offline/low-token iteration.



