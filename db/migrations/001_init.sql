-- db/migrations/001_init.sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE sources (
  id          BIGSERIAL PRIMARY KEY,
  name        TEXT NOT NULL,
  kind        TEXT NOT NULL CHECK (kind IN ('docs','github_release')),
  seed_url    TEXT NOT NULL,
  crawl_rules JSONB NOT NULL DEFAULT '{}'::jsonb,
  enabled     BOOLEAN NOT NULL DEFAULT TRUE,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE documents (
  id           BIGSERIAL PRIMARY KEY,
  source_id    BIGINT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
  url          TEXT NOT NULL UNIQUE,
  title        TEXT NOT NULL,
  version      TEXT,
  content_text TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  fetched_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  status       TEXT NOT NULL DEFAULT 'ingested'
                 CHECK (status IN ('ingested','embedded','failed'))
);

CREATE TABLE chunks (
  id          BIGSERIAL PRIMARY KEY,
  document_id BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  ordinal     INT NOT NULL,
  text        TEXT NOT NULL,
  embedding   vector(768) NOT NULL,
  token_count INT NOT NULL,
  UNIQUE (document_id, ordinal)
);

CREATE INDEX chunks_embedding_hnsw
  ON chunks USING hnsw (embedding vector_cosine_ops);
