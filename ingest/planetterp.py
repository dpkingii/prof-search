import hashlib
import json
import time
from collections.abc import Callable, Iterator
from pathlib import Path

import httpx

BASE_URL = "https://planetterp.com/api/v1"
PAGE_SIZE = 100  # API maximum


class PlanetTerp:
    """PlanetTerp client with throttling, retry on 429/5xx, and an on-disk response cache."""

    def __init__(
        self,
        cache_dir: Path = Path(".cache/planetterp"),
        refresh: bool = False,
        min_interval: float = 0.2,
        max_retries: int = 5,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.cache_dir = cache_dir
        self.refresh = refresh
        self.min_interval = min_interval
        self.max_retries = max_retries
        self.sleep = sleep
        self.http = httpx.Client(base_url=BASE_URL, timeout=30, transport=transport)
        self._last_request = 0.0
        cache_dir.mkdir(parents=True, exist_ok=True)

    def professors(self, max_pages: int | None = None) -> Iterator[dict]:
        offset = 0
        pages = 0
        while max_pages is None or pages < max_pages:
            page = self._get(
                "/professors",
                {"type": "professor", "reviews": "true", "limit": PAGE_SIZE, "offset": offset},
            )
            if not page:
                return
            yield from page
            offset += PAGE_SIZE
            pages += 1

    def grades(self, professor_name: str) -> list[dict]:
        return self._get("/grades", {"professor": professor_name}) or []

    def _get(self, path: str, params: dict) -> list | None:
        cache_file = self._cache_path(path, params)
        if not self.refresh and cache_file.exists():
            return json.loads(cache_file.read_text())

        for attempt in range(self.max_retries):
            self._throttle()
            resp = self.http.get(path, params=params)
            if resp.status_code == 429 or resp.status_code >= 500:
                self.sleep(2**attempt)
                continue
            if resp.status_code == 404:
                data = None
            else:
                resp.raise_for_status()
                data = resp.json()
            cache_file.write_text(json.dumps(data))
            return data
        raise RuntimeError(f"{path} {params}: gave up after {self.max_retries} attempts")

    def _cache_path(self, path: str, params: dict) -> Path:
        key = path + "?" + "&".join(f"{k}={params[k]}" for k in sorted(params))
        return self.cache_dir / (hashlib.sha256(key.encode()).hexdigest() + ".json")

    def _throttle(self) -> None:
        wait = self._last_request + self.min_interval - time.monotonic()
        if wait > 0:
            self.sleep(wait)
        self._last_request = time.monotonic()
