# review-search

Search 46k+ UMD professor reviews from [PlanetTerp](https://planetterp.com) by meaning, not just keywords.

Four retrieval modes over the same data, keyword (Postgres full-text), vector (bge-small + pgvector HNSW), hybrid (reciprocal rank fusion), and a cross-encoder reranker, compared on 60 graded queries. Reranking raises nDCG@10 from 0.509 (keyword) and 0.636 (hybrid) to 0.735, at 155 ms p50. Full numbers are in [Results](#results).

![The query "not much homework" in hybrid and rerank modes side by side](docs/hybrid-vs-rerank.png)

Same query, two modes. Hybrid returns reviews that contain "not", "much" and "homework" but complain about the homework. Rerank returns reviews that say there isn't much of it.

## Run locally

Requires Docker and Python 3.12+.

```sh
make venv      # create .venv and install deps
make db        # Postgres + pgvector on localhost:5433
make migrate
make ingest    # ~145 API requests (~6 min first run), cached under .cache/
make embed     # chunk + embed new reviews (~22 min on CPU), --rebuild after changing chunking
make api       # search page at http://localhost:8000, API docs at /docs
```

```sh
curl 'localhost:8000/search?q=not+much+homework&k=5'   # mode=rerank (default), hybrid, vector, keyword
```

`python -m ingest.load --grades` also pulls grade distributions (one request per professor) to fill `average_gpa`.

## How a query runs

1. **Keyword:** Postgres full-text search over reviews, matching any query word, top 50 reviews.
2. **Vector:** the query is embedded with bge-small and matched against 54k review chunks through an HNSW index, top 50 reviews.
3. **Hybrid:** the two lists are merged with reciprocal rank fusion, which only looks at ranks, so the two score scales never need to agree.
4. **Rerank:** a MiniLM cross-encoder reads the query next to each of the top 50 fused reviews and rescores them.
5. Reviews are collapsed into professors. A professor scores the rank-discounted sum of their best three reviews.

## Results

60 queries across five types (teaching, grading, workload, course, contrast). For each query the top 10 professors from every mode were pooled and graded 0/1/2 from their matching snippets, 1,413 judgments in total. Unjudged professors count as not relevant, so recall is relative to the pool.

| Method | Recall@10 | MRR | nDCG@10 | p50 ms | p95 ms |
|---|---|---|---|---|---|
| keyword | 0.374 | 0.764 | 0.509 | 40.0 | 72.3 |
| vector | 0.479 | 0.849 | 0.604 | 7.8 | 14.1 |
| hybrid | 0.494 | 0.872 | 0.636 | 54.6 | 89.4 |
| rerank | 0.547 | 0.893 | 0.735 | 154.5 | 189.9 |

nDCG@10 by query type:

| Type | n | keyword | vector | hybrid | rerank |
|---|---|---|---|---|---|
| contrast | 12 | 0.439 | 0.633 | 0.649 | 0.745 |
| course | 11 | 0.290 | 0.723 | 0.574 | 0.703 |
| grading | 13 | 0.598 | 0.560 | 0.689 | 0.732 |
| teaching | 12 | 0.766 | 0.652 | 0.711 | 0.860 |
| workload | 12 | 0.427 | 0.463 | 0.548 | 0.633 |

Latency is in-process on an M4 Pro laptop, one query at a time, and includes embedding the query.

## Where each mode fails

**Keyword search ranks short generic reviews first.** Matching any query word means "good for ECON200" also matches every review containing "good", and `ts_rank` normalizes by length, so one-word reviews like "Good." outrank the review that actually discusses ECON200. Keyword scored 0.00 on that query and 0.10 on "best professor for MATH140", where vector scored 1.00 and 0.88. "STAT400 exams" fails the same way (keyword 0.00): short reviews like "Easy exams hw and projects" outrank the ones that mention STAT400.

**Vector search loses exact details.** Queries that hinge on a specific policy or phrase go to keyword: "uses lots of real world examples" (keyword 0.72, vector 0.03), "drops the lowest exam score" (0.57 vs 0.16), "weekly quizzes" (1.00 vs 0.54). The embedding finds reviews about the general topic, like exams or grading, without the detail that makes them relevant.

**Neither first-stage mode handles negation.** "no exams, just projects" scored 0.04 for keyword and 0.00 for vector and hybrid. Every top result talks about exams and projects, usually both. "lenient grader who curves exams" pulls in "does not curve" and "refuses to curve", since the negated review shares nearly all its words and most of its meaning with the query.

**Fusion helps on average but can bury a strong single list.** Hybrid beats both inputs overall and on grading and workload queries, where each mode catches different relevant reviews. On course queries it lands below vector alone (0.574 vs 0.723) because keyword's generic matches take up half the fused ranking. "avoid for CMSC351" dropped from 0.51 (vector) to 0.10 (hybrid).

## What reranking fixed, and what it didn't

The cross-encoder reads the query and review as one input instead of comparing two separate embeddings, so "not much homework" and "tons of homework" no longer look alike. It lifted nDCG@10 from 0.636 (hybrid) to 0.735 and won four of five query types.

| Query | hybrid | rerank |
|---|---|---|
| not much homework | 0.31 | 0.86 |
| uses lots of real world examples | 0.16 | 0.83 |
| drops the lowest exam score | 0.39 | 0.68 |
| no exams, just projects | 0.00 | 0.41 |
| lenient grader who curves exams | 0.68 | 0.40 |

It still misses. "lenient grader who curves exams" got worse because reviews like "She doesn't curve but she does offer extra credit and is a very lenient grader" match the strongest phrase in the query, and the model weighs that over the negated part. Course queries are still best served by vector alone, since the reranker can only reorder what fusion hands it.

**Tuning.** The cross-encoder runs once per (query, review) pair, so latency grows with both the number of candidates and their length. These sweeps ran before the last 37 judgments were added, so the absolute numbers differ slightly from the table above.

| Candidates reranked (full text) | nDCG@10 | p50 ms |
|---|---|---|
| 10 | 0.624 | 79 |
| 20 | 0.644 | 162 |
| 30 | 0.639 | 238 |
| 50 | 0.695 | 456 |

| Words fed to the reranker (50 candidates) | nDCG@10 | p50 ms |
|---|---|---|
| 48 | 0.736 | 136 |
| 64 | 0.721 | 161 |
| 96 | 0.698 | 227 |
| 128 | 0.693 | 275 |
| full chunk (up to 200) | 0.695 | 456 |

The shipped setting is 50 candidates truncated to 64 words, close to the ~56-word average passage in MS MARCO, which the model was trained on. One caveat: graders saw roughly the first 30 words of each professor's top two snippets, so a reranker that only reads the start of a review is looking at the same text the grader did. Part of the gain from truncation may come from that rather than from the model.

## Load test

`load/search.js` is a closed-loop k6 test: each virtual user sends a random eval query, waits for the response, and repeats. Single uvicorn process on the same laptop, 20 s per run, no failed requests.

| Mode | Users | Req/s | p50 ms | p95 ms | p99 ms |
|---|---|---|---|---|---|
| vector | 1 | 114 | 9 | 10 | 13 |
| vector | 10 | 282 | 35 | 48 | 71 |
| hybrid | 1 | 18 | 53 | 85 | 104 |
| hybrid | 10 | 62 | 158 | 213 | 243 |
| rerank | 1 | 6 | 172 | 213 | 253 |
| rerank | 10 | 12 | 803 | 1,120 | 1,200 |

Reranking is CPU bound and saturates around 12 req/s on this machine, so ten concurrent users mostly wait in line. Hybrid's ceiling comes from the keyword half. Vector search alone stays fast under load.

## Next steps

- Treat course codes as exact filters instead of free text. This is the one query type reranking doesn't win.
- Cap how much very short reviews can score in keyword search. It would help hybrid and give the reranker better candidates.
- Re-grade a sample of judgments with snippets from later in each review to measure the truncation bias above.

## Evaluate

Queries and judgments live in `eval/queries.jsonl`.

```sh
make label     # pool top professors from every mode and grade the unjudged ones
make eval      # Recall@10, MRR, nDCG@10, latency per mode -> eval/results.md
make loadtest  # k6 against a running API, override with MODE=hybrid VUS=10
```

## Test

```sh
make test      # integration tests use the review_test database from docker compose
make lint
```
