60 labeled queries, k=10. Latency is in-process and includes query embedding.

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
