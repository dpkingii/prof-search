from index.embed import index_reviews
from search import vector
from tests.helpers import FakeEmbedder
from tests.test_keyword_search import seed

embedder = FakeEmbedder()


def whole_review(text: str) -> list[str]:
    return [text]


def halves(text: str) -> list[str]:
    words = text.split()
    mid = len(words) // 2
    return [" ".join(words[:mid]), " ".join(words[mid:])]


def test_index_reviews_is_incremental(conn):
    seed(conn)
    assert index_reviews(conn, embedder, chunker=whole_review) == 3
    assert index_reviews(conn, embedder, chunker=whole_review) == 0


def test_index_reviews_survives_chunker_returning_nothing(conn):
    seed(conn)
    assert index_reviews(conn, embedder, chunker=lambda _: []) == 0


def test_nearest_review_first(conn):
    seed(conn)
    index_reviews(conn, embedder, chunker=whole_review)
    results = vector.search(conn, embedder.query("brutal exams never curves"), k=3)
    assert results[0]["professor_slug"] == "jones"
    assert results[0]["score"] > results[1]["score"]


def test_one_hit_per_review_with_best_chunk(conn):
    seed(conn)
    index_reviews(conn, embedder, chunker=halves)
    results = vector.search(conn, embedder.query("lecture slides"), k=10)

    ids = [r["id"] for r in results]
    assert len(ids) == len(set(ids)) == 3
    assert "slides" in results[0]["chunk"]
