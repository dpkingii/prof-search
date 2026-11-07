import pytest
from fastapi.testclient import TestClient

from api.main import app, get_embedder, get_reranker
from index.embed import index_reviews
from tests.helpers import FakeEmbedder, FakeReranker
from tests.test_keyword_search import seed


@pytest.fixture
def client(conn):
    seed(conn)
    embedder = FakeEmbedder()
    index_reviews(conn, embedder, chunker=lambda text: [text])
    app.dependency_overrides[get_embedder] = lambda: embedder
    app.dependency_overrides[get_reranker] = FakeReranker
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_healthz_and_professor(client):
    assert client.get("/healthz").json() == {"ok": True}
    prof = client.get("/professors/smith").json()
    assert prof["review_count"] == 2
    assert client.get("/professors/nobody").status_code == 404


def test_search_validation(client):
    assert client.get("/search", params={"q": ""}).status_code == 422
    assert client.get("/search", params={"q": "x", "mode": "bogus"}).status_code == 422


@pytest.mark.parametrize("mode", ["keyword", "vector", "hybrid", "rerank"])
def test_search_returns_professors(client, mode):
    body = client.get("/search", params={"q": "exams brutal never curves", "mode": mode}).json()
    assert body["mode"] == mode
    assert body["results"][0]["slug"] == "jones"
    assert body["results"][0]["snippets"]


def test_serves_search_page(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Review Search" in resp.text


def test_default_mode_is_rerank(client):
    assert client.get("/search", params={"q": "exams"}).json()["mode"] == "rerank"
