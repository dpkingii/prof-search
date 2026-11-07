# review-search

Search 46k+ UMD professor reviews from [PlanetTerp](https://planetterp.com) by meaning, not just keywords.

Status: week 2. Keyword (Postgres full-text), vector (bge-small + pgvector HNSW), and hybrid (reciprocal rank fusion) search, evaluated on 60 graded queries.

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

`python -m ingest.load --grades` also pulls grade distributions (one request per professor) to fill `average_gpa`.

## Results

60 queries across five types (teaching, grading, workload, course, contrast). For each query the top 10 professors from every mode were pooled and graded 0/1/2 from their matching snippets, 1,178 judgments in total. Unjudged professors count as not relevant, so recall is relative to the pool.

| Method | Recall@10 | MRR | nDCG@10 | p50 ms | p95 ms |
|---|---|---|---|---|---|
| keyword | 0.465 | 0.764 | 0.539 | 34.6 | 64.0 |
| vector | 0.573 | 0.849 | 0.635 | 11.3 | 19.1 |
| hybrid | 0.595 | 0.872 | 0.670 | 45.7 | 75.4 |

nDCG@10 by query type:

| Type | n | keyword | vector | hybrid |
|---|---|---|---|---|
| contrast | 12 | 0.467 | 0.679 | 0.697 |
| course | 11 | 0.304 | 0.764 | 0.608 |
| grading | 13 | 0.638 | 0.596 | 0.737 |
| teaching | 12 | 0.790 | 0.660 | 0.721 |
| workload | 12 | 0.467 | 0.491 | 0.576 |

Latency is in-process on an M4 Pro laptop and includes embedding the query. Hybrid pays for both searches, and the keyword half is the slow one.

## Where each mode fails

**Keyword search ranks short generic reviews first.** Matching any query word means "good for ECON200" also matches every review containing "good", and `ts_rank` normalizes by length, so one-word reviews like "Good." outrank the review that actually discusses ECON200. Keyword scored 0.00 on that query and 0.10 on "best professor for MATH140", where vector scored 1.00 and 0.88. "STAT400 exams" fails the same way (keyword 0.00): short reviews like "Easy exams hw and projects" outrank the ones that mention STAT400.

**Vector search loses exact details.** Queries that hinge on a specific policy or phrase go to keyword: "uses lots of real world examples" (keyword 0.87, vector 0.04), "drops the lowest exam score" (0.62 vs 0.17), "weekly quizzes" (1.00 vs 0.54). The embedding finds reviews about the general topic, like exams or grading, without the detail that makes them relevant.

**Neither mode handles negation.** "no exams, just projects" scored 0.30 for keyword and 0.00 for vector and hybrid. Every top result talks about exams and projects, usually both. "lenient grader who curves exams" pulls in "does not curve" and "refuses to curve" in both modes, since the negated review shares nearly all its words and most of its meaning with the query.

**Fusion helps on average but can bury a strong single list.** Hybrid has the best overall score and wins on grading and workload queries, where each mode catches different relevant reviews. On course queries it lands below vector alone (0.608 vs 0.764) because keyword's generic matches take up half the fused ranking. "avoid for CMSC351" dropped from 0.51 (vector) to 0.10 (hybrid).

These point to three next steps:

- A cross-encoder reranker over the fused top 50. It reads the query and review together, so it should catch negation.
- Treating course codes as exact filters instead of free text.
- Capping how much very short reviews can score.

## Evaluate

Queries and judgments live in `eval/queries.jsonl`.

```sh
make label     # pool top professors from every mode and grade the unjudged ones
make eval      # Recall@10, MRR, nDCG@10, latency per mode -> eval/results.md
```

## Test

```sh
make test      # integration tests use the review_test database from docker compose
make lint
```
