import httpx

from ingest.planetterp import PAGE_SIZE, PlanetTerp


def make_client(tmp_path, handler, **kwargs):
    return PlanetTerp(
        cache_dir=tmp_path,
        min_interval=0,
        transport=httpx.MockTransport(handler),
        sleep=lambda _: None,
        **kwargs,
    )


def test_professors_paginates_until_empty_page(tmp_path):
    offsets = []

    def handler(request):
        offset = int(request.url.params["offset"])
        offsets.append(offset)
        page = [{"slug": f"p{offset}"}] if offset < 2 * PAGE_SIZE else []
        return httpx.Response(200, json=page)

    profs = list(make_client(tmp_path, handler).professors())

    assert [p["slug"] for p in profs] == ["p0", f"p{PAGE_SIZE}"]
    assert offsets == [0, PAGE_SIZE, 2 * PAGE_SIZE]


def test_max_pages(tmp_path):
    client = make_client(tmp_path, lambda r: httpx.Response(200, json=[{"slug": "x"}]))
    assert len(list(client.professors(max_pages=3))) == 3


def test_retries_on_429_and_5xx(tmp_path):
    responses = iter([httpx.Response(429), httpx.Response(503), httpx.Response(200, json=[])])
    calls = []

    def handler(request):
        calls.append(request)
        return next(responses)

    assert make_client(tmp_path, handler).grades("Someone") == []
    assert len(calls) == 3


def test_cache_hit_skips_network(tmp_path):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=[{"A": 3}])

    make_client(tmp_path, handler).grades("Someone")
    assert make_client(tmp_path, handler).grades("Someone") == [{"A": 3}]
    assert len(calls) == 1


def test_refresh_bypasses_cache(tmp_path):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=[])

    make_client(tmp_path, handler).grades("Someone")
    make_client(tmp_path, handler, refresh=True).grades("Someone")
    assert len(calls) == 2


def test_grades_404_is_empty(tmp_path):
    assert make_client(tmp_path, lambda r: httpx.Response(404)).grades("Nobody") == []
