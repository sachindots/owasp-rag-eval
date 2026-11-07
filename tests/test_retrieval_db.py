import psycopg
import pytest

from owasp_rag.db import connect
from owasp_rag.retrieval import keyword_search


@pytest.fixture(scope="module")
def conn():
    try:
        c = connect()
    except psycopg.OperationalError:
        pytest.skip("needs `make db ingest`")
    if not c.execute("SELECT to_regclass('chunks') IS NOT NULL").fetchone()[0]:
        pytest.skip("needs `make ingest`")
    yield c
    c.close()


def test_keyword_search_matches_a_long_natural_question(conn):
    q = "What minimum Argon2id settings does OWASP recommend for password hashing?"
    hits = keyword_search(conn, q, 5)
    assert len(hits) == 5
    assert any(h.doc == "Password_Storage_Cheat_Sheet" for h in hits)


def test_keyword_search_with_only_stopwords_returns_nothing(conn):
    assert keyword_search(conn, "what is it and how is it", 5) == []
