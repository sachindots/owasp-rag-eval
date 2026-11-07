from collections.abc import Sequence

import numpy as np
import psycopg

from .llm import embed
from .schemas import Chunk

_COLUMNS = "id, doc, heading, text"


def _chunks(rows: list[tuple]) -> list[Chunk]:
    return [Chunk(id=r[0], doc=r[1], heading=r[2], text=r[3]) for r in rows]


def vector_search(conn: psycopg.Connection, query_embedding: list[float], k: int) -> list[Chunk]:
    """Top k chunks by cosine distance (pgvector's `<=>` on chunks.embedding), nearest first."""
    rows = conn.execute(
        f"SELECT {_COLUMNS} FROM chunks ORDER BY embedding <=> %s LIMIT %s",
        (np.asarray(query_embedding, dtype=np.float32), k),
    ).fetchall()
    return _chunks(rows)


def keyword_search(conn: psycopg.Connection, query: str, k: int) -> list[Chunk]:
    """Top k chunks by Postgres full-text rank, best first.

    Use websearch_to_tsquery('english', query) against chunks.tsv and order by ts_rank_cd.
    This is not BM25. If you want BM25, compute it in memory over all chunks and say so in PLAN.md.
    """
    rows = conn.execute(
        f"SELECT {_COLUMNS} FROM chunks, websearch_to_tsquery('english', %(q)s) query"
        " WHERE tsv @@ query ORDER BY ts_rank_cd(tsv, query) DESC, id LIMIT %(k)s",
        {"q": query, "k": k},
    ).fetchall()
    return _chunks(rows)


def rrf_merge(rankings: Sequence[Sequence[Chunk]], k: int = 60) -> list[Chunk]:
    """Reciprocal rank fusion.

    score(chunk) = sum over the rankings that contain it of 1 / (k + rank), rank starting at 1.
    Chunks are identified by id. Return each chunk once, highest score first. Ties keep the
    order in which the chunks first appear across the rankings.
    """
    scores: dict[str, float] = {}
    chunks: dict[str, Chunk] = {}
    for ranking in rankings:
        for rank, chunk in enumerate(ranking, start=1):
            scores[chunk.id] = scores.get(chunk.id, 0.0) + 1 / (k + rank)
            chunks.setdefault(chunk.id, chunk)
    # sorted() is stable and dicts keep insertion order, so ties keep first appearance.
    return [chunks[cid] for cid in sorted(scores, key=lambda cid: -scores[cid])]


def hybrid_search(conn: psycopg.Connection, query: str, k: int) -> list[Chunk]:
    """Embed the query, run both searches with a deeper cut than k (4 * k is a fine start),
    merge them with rrf_merge, and return the top k."""
    depth = 4 * k
    dense = vector_search(conn, embed([query])[0], depth)
    return rrf_merge([dense, keyword_search(conn, query, depth)])[:k]
