60 labeled queries, k=10. Latency is in-process and includes query embedding.

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
