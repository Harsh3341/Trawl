from __future__ import annotations
import os
from dataclasses import dataclass
import psycopg
from pgvector.psycopg import register_vector


@dataclass(frozen=True)
class StoredChunk:
    ordinal: int
    text: str
    token_count: int
    embedding: list[float]


class Database:
    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn

    @classmethod
    def connect(cls, dsn: str | None = None) -> "Database":
        conn = psycopg.connect(dsn or os.environ["DATABASE_URL"], autocommit=True)
        register_vector(conn)
        return cls(conn)

    def truncate_all(self) -> None:
        self._conn.execute("TRUNCATE sources, documents, chunks RESTART IDENTITY CASCADE")

    def ensure_source(self, name: str, kind: str, seed_url: str) -> int:
        with self._conn.cursor() as cur:
            cur.execute("SELECT id FROM sources WHERE seed_url = %s", (seed_url,))
            row = cur.fetchone()
            if row:
                return row[0]
            cur.execute("INSERT INTO sources (name, kind, seed_url) VALUES (%s,%s,%s) RETURNING id",
                        (name, kind, seed_url))
            return cur.fetchone()[0]

    def upsert_document(self, source_id, url, title, version, content_text, content_hash) -> tuple[int, bool]:
        with self._conn.cursor() as cur:
            cur.execute("""
                INSERT INTO documents (source_id, url, title, version, content_text, content_hash, status)
                VALUES (%s,%s,%s,%s,%s,%s,'ingested')
                ON CONFLICT (url) DO UPDATE SET
                    title=EXCLUDED.title, version=EXCLUDED.version,
                    content_text=EXCLUDED.content_text, content_hash=EXCLUDED.content_hash,
                    status='ingested', fetched_at=now()
                WHERE documents.content_hash <> EXCLUDED.content_hash
                RETURNING id""",
                (source_id, url, title, version, content_text, content_hash))
            row = cur.fetchone()
            if row:
                return row[0], True
            cur.execute("SELECT id FROM documents WHERE url = %s", (url,))
            return cur.fetchone()[0], False

    def replace_chunks(self, document_id: int, chunks: list[StoredChunk]) -> None:
        with self._conn.cursor() as cur:
            cur.execute("DELETE FROM chunks WHERE document_id = %s", (document_id,))
            for c in chunks:
                cur.execute(
                    """INSERT INTO chunks (document_id, ordinal, text, embedding, token_count)
                       VALUES (%s,%s,%s,%s,%s)""",
                    (document_id, c.ordinal, c.text, c.embedding, c.token_count))
            cur.execute("UPDATE documents SET status='embedded' WHERE id = %s", (document_id,))

    def count_chunks(self, document_id: int) -> int:
        with self._conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM chunks WHERE document_id = %s", (document_id,))
            return cur.fetchone()[0]

    def document_status(self, document_id: int) -> str:
        with self._conn.cursor() as cur:
            cur.execute("SELECT status FROM documents WHERE id = %s", (document_id,))
            return cur.fetchone()[0]
