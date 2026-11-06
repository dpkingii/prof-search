# review-search

Search 46k+ UMD professor reviews from [PlanetTerp](https://planetterp.com) by meaning, not just keywords.

Status: week 2. Keyword (Postgres full-text), vector (bge-small + pgvector HNSW), and hybrid (reciprocal rank fusion) search, with an eval harness to compare them.

## Run locally

Requires Docker and Python 3.12+.

```sh
make venv      # create .venv and install deps
make db        # Postgres + pgvector on localhost:5433
make migrate
make ingest    # ~145 API requests (~6 min first run), cached under .cache/
make embed     # chunk + embed new reviews; --rebuild after changing chunking
make api       # http://localhost:8000/docs
```

```sh
curl 'localhost:8000/search?q=lenient+grader+posts+slides&k=5&mode=hybrid'   # or keyword, vector
```

## Evaluate

Queries and graded judgments (0/1/2 per professor) live in `eval/queries.jsonl`.

```sh
make label     # pool top professors from every mode and grade the unjudged ones
make eval      # Recall@10, MRR, nDCG@10, latency per mode -> eval/results.md
```

`python -m ingest.load --grades` also pulls grade distributions (one request per professor) to fill `average_gpa`.

## Test

```sh
make test      # integration tests use the review_test database from docker compose
make lint
```
