from collections.abc import Sequence
from pathlib import Path

import numpy as np
import psycopg
from pgvector.psycopg import register_vector

from .config import settings
from .schemas import Chunk

SCHEMA_SQL = (Path(__file__).parent / "schema.sql").read_text()


def connect() -> psycopg.Connection:
    conn = psycopg.connect(settings.database_url, autocommit=True)
    # The extension must exist before register_vector can look up the type.
    conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    register_vector(conn)
    return conn


def init_schema(conn: psycopg.Connection) -> None:
    conn.execute(SCHEMA_SQL)


def replace_chunks(
    conn: psycopg.Connection, chunks: Sequence[Chunk], embeddings: Sequence[Sequence[float]]
) -> None:
    """Swap the whole index in one transaction, so a re-ingest never leaves stale chunk ids."""
    if len(chunks) != len(embeddings):
        raise ValueError(f"{len(chunks)} chunks but {len(embeddings)} embeddings")
    with conn.transaction():
        conn.execute("TRUNCATE chunks")
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO chunks (id, doc, heading, text, embedding)"
                " VALUES (%s, %s, %s, %s, %s)",
                [
                    (c.id, c.doc, c.heading, c.text, np.asarray(e, dtype=np.float32))
                    for c, e in zip(chunks, embeddings, strict=True)
                ],
            )
