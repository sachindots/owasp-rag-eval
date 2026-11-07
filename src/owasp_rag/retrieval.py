from collections.abc import Sequence

import psycopg

from .schemas import Chunk


def vector_search(conn: psycopg.Connection, query_embedding: list[float], k: int) -> list[Chunk]:
    """Top k chunks by cosine distance (pgvector's `<=>` on chunks.embedding), nearest first."""
    raise NotImplementedError


def keyword_search(conn: psycopg.Connection, query: str, k: int) -> list[Chunk]:
    """Top k chunks by Postgres full-text rank, best first.

    Use websearch_to_tsquery('english', query) against chunks.tsv and order by ts_rank_cd.
    This is not BM25. If you want BM25, compute it in memory over all chunks and say so in PLAN.md.
    """
    raise NotImplementedError


def rrf_merge(rankings: Sequence[Sequence[Chunk]], k: int = 60) -> list[Chunk]:
    """Reciprocal rank fusion.

    score(chunk) = sum over the rankings that contain it of 1 / (k + rank), rank starting at 1.
    Chunks are identified by id. Return each chunk once, highest score first. Ties keep the
    order in which the chunks first appear across the rankings.
    """
    raise NotImplementedError


def hybrid_search(conn: psycopg.Connection, query: str, k: int) -> list[Chunk]:
    """Embed the query, run both searches with a deeper cut than k (4 * k is a fine start),
    merge them with rrf_merge, and return the top k."""
    raise NotImplementedError
