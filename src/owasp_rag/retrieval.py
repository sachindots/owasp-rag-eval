import math
from collections import Counter, defaultdict
from collections.abc import Sequence

import numpy as np
import psycopg

from .llm import embed
from .schemas import Chunk, RetrievalHit

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


class Bm25:
    """Okapi BM25 over pre-tokenised documents: term -> count per document id."""

    def __init__(self, docs: dict[str, Counter[str]], k1: float = 1.2, b: float = 0.75):
        self.k1, self.b = k1, b
        self.length = {d: sum(tf.values()) for d, tf in docs.items()}
        self.avg_length = sum(self.length.values()) / len(docs) if docs else 0.0
        self.postings: dict[str, list[tuple[str, int]]] = defaultdict(list)
        for d, tf in docs.items():
            for term, n in tf.items():
                self.postings[term].append((d, n))

    def top(self, terms: Sequence[str], k: int) -> list[str]:
        """Ids of the k best documents for the query terms, best first; ties break by id."""
        n_docs = len(self.length)
        scores: dict[str, float] = defaultdict(float)
        for term in set(terms):
            postings = self.postings.get(term, [])
            idf = math.log(1 + (n_docs - len(postings) + 0.5) / (len(postings) + 0.5))
            for d, n in postings:
                norm = 1 - self.b + self.b * self.length[d] / self.avg_length
                scores[d] += idf * n * (self.k1 + 1) / (n + self.k1 * norm)
        return sorted(scores, key=lambda d: (-scores[d], d))[:k]


# shortcut: the index is built once per process; restart the process after `make ingest`.
_index: tuple[Bm25, dict[str, Chunk]] | None = None


def _bm25_index(conn: psycopg.Connection) -> tuple[Bm25, dict[str, Chunk]]:
    global _index
    if _index is None:
        chunks = {c.id: c for c in _chunks(conn.execute(f"SELECT {_COLUMNS} FROM chunks"))}
        docs: dict[str, Counter[str]] = defaultdict(Counter)
        # Reuse the lexemes Postgres already stored in chunks.tsv, so documents and queries
        # share the 'english' stemmer and stopword list.
        for cid, lexeme, n in conn.execute(
            "SELECT id, t.lexeme, cardinality(t.positions) FROM chunks, unnest(tsv) t"
        ):
            docs[cid][lexeme] = n
        _index = (Bm25(docs), chunks)
    return _index


def keyword_search(conn: psycopg.Connection, query: str, k: int) -> list[Chunk]:
    """Top k chunks by BM25, best first.

    In memory over the lexemes in chunks.tsv. Postgres's ts_rank_cd has no IDF and found
    the evidence for 42% of dev questions against BM25's 79% (PLAN.md, decisions log).
    A question made only of stopwords has no terms and returns no chunks.
    """
    index, chunks = _bm25_index(conn)
    (terms,) = conn.execute(
        "SELECT tsvector_to_array(to_tsvector('english', %s))", (query,)
    ).fetchone()
    return [chunks[cid] for cid in index.top(terms, k)]


def _rrf_scores(rankings: Sequence[Sequence[Chunk]], k: int) -> dict[str, float]:
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, chunk in enumerate(ranking, start=1):
            scores[chunk.id] = scores.get(chunk.id, 0.0) + 1 / (k + rank)
    return scores


def rrf_merge(rankings: Sequence[Sequence[Chunk]], k: int = 60) -> list[Chunk]:
    """Reciprocal rank fusion.

    score(chunk) = sum over the rankings that contain it of 1 / (k + rank), rank starting at 1.
    Chunks are identified by id. Return each chunk once, highest score first. Ties keep the
    order in which the chunks first appear across the rankings.
    """
    scores = _rrf_scores(rankings, k)
    chunks = {c.id: c for ranking in reversed(rankings) for c in reversed(ranking)}
    # sorted() is stable and dicts keep insertion order, so ties keep first appearance.
    return [chunks[cid] for cid in sorted(scores, key=lambda cid: -scores[cid])]


def hybrid_search(conn: psycopg.Connection, query: str, k: int) -> list[Chunk]:
    """Embed the query, run both searches with a deeper cut than k (4 * k is a fine start),
    merge them with rrf_merge, and return the top k."""
    return [chunk for chunk, _ in traced_hybrid_search(conn, query, k)]


def traced_hybrid_search(
    conn: psycopg.Connection, query: str, k: int
) -> list[tuple[Chunk, RetrievalHit]]:
    """hybrid_search, with each chunk's dense rank, keyword rank and fused score."""
    depth = 4 * k
    dense = vector_search(conn, embed([query])[0], depth)
    keyword = keyword_search(conn, query, depth)
    scores = _rrf_scores([dense, keyword], 60)
    dense_rank = {c.id: n for n, c in enumerate(dense, start=1)}
    keyword_rank = {c.id: n for n, c in enumerate(keyword, start=1)}
    return [
        (
            chunk,
            RetrievalHit(
                id=chunk.id,
                dense_rank=dense_rank.get(chunk.id),
                keyword_rank=keyword_rank.get(chunk.id),
                rrf_score=scores[chunk.id],
            ),
        )
        for chunk in rrf_merge([dense, keyword])[:k]
    ]
