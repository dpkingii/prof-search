# review-search

Search 46k+ UMD professor reviews from [PlanetTerp](https://planetterp.com) by meaning, not just keywords.

Status: week 1, keyword (Postgres full-text) baseline. Vector and hybrid search come next.

## Run locally

Requires Docker and Python 3.12+.

```sh
make venv      # create .venv and install deps
make db        # Postgres + pgvector on localhost:5433
make migrate
make ingest    # ~145 API requests (~6 min first run), cached under .cache/
make api       # http://localhost:8000/docs
```

```sh
curl 'localhost:8000/search?q=lenient+grader+posts+slides&k=5'
```

`python -m ingest.load --grades` also pulls grade distributions (one request per professor) to fill `average_gpa`.

## Test

```sh
make test      # integration tests use the review_test database from docker compose
make lint
```
