import pytest
from fastapi.testclient import TestClient

from api.main import app, get_embedder
from index.embed import index_reviews
from tests.helpers import FakeEmbedder, needs_impl
from tests.test_keyword_search import seed


@pytest.fixture
def client(conn):
    seed(conn)
    embedder = FakeEmbedder()
    index_reviews(conn, embedder, chunker=lambda text: [text])
    app.dependency_overrides[get_embedder] = lambda: embedder
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


@needs_impl
@pytest.mark.parametrize("mode", ["keyword", "vector", "hybrid"])
def test_search_returns_professors(client, mode):
    body = client.get("/search", params={"q": "exams brutal never curves", "mode": mode}).json()
    assert body["mode"] == mode
    assert body["results"][0]["slug"] == "jones"
    assert body["results"][0]["snippets"]
