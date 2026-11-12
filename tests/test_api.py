import pytest
from fastapi.testclient import TestClient

from api.main import app, get_embedder, get_reranker
from index.embed import index_reviews
from ingest.umdio import replace_gen_ed_courses
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


@pytest.mark.parametrize("mode", ["keyword", "vector", "hybrid", "rerank"])
def test_gen_eds_returns_only_gen_ed_courses(client, conn, mode):
    replace_gen_ed_courses(conn, [{"course_id": "MATH140", "name": "Calculus I",
                                   "gen_eds": ["FSAR", "FSMA"]}])
    conn.commit()
    params = {"q": "lenient grader brutal exams", "mode": mode}

    results = client.get("/gen-eds", params=params).json()["results"]
    assert [c["course_id"] for c in results] == ["MATH140"]
    assert results[0]["name"] == "Calculus I"
    assert results[0]["gen_eds"] == ["FSAR", "FSMA"]
    assert results[0]["snippets"]

    assert client.get("/gen-eds", params={**params, "gen_ed": "FSMA"}).json()["results"]
    assert client.get("/gen-eds", params={**params, "gen_ed": "DSHU"}).json()["results"] == []


def test_gen_eds_default_mode_is_hybrid(client):
    assert client.get("/gen-eds", params={"q": "exams"}).json()["mode"] == "hybrid"


def test_gen_eds_validation(client):
    assert client.get("/gen-eds", params={"q": "x", "gen_ed": "BOGUS"}).status_code == 422
