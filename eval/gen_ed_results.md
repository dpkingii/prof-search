20 labeled queries, k=10. Latency is in-process and includes query embedding.

| Method | Recall@10 | MRR | nDCG@10 | p50 ms | p95 ms |
|---|---|---|---|---|---|
| keyword | 0.474 | 0.950 | 0.567 | 16.0 | 36.1 |
| vector | 0.557 | 0.925 | 0.628 | 31.8 | 45.4 |
| hybrid | 0.566 | 0.975 | 0.670 | 44.6 | 57.1 |
| rerank | 0.548 | 0.850 | 0.646 | 155.8 | 194.4 |

nDCG@10 by query type:

| Type | n | keyword | vector | hybrid | rerank |
|---|---|---|---|---|---|
| easy | 5 | 0.664 | 0.727 | 0.717 | 0.669 |
| format | 3 | 0.580 | 0.511 | 0.615 | 0.755 |
| grading | 4 | 0.559 | 0.642 | 0.673 | 0.672 |
| interest | 4 | 0.623 | 0.716 | 0.730 | 0.701 |
| workload | 4 | 0.390 | 0.488 | 0.589 | 0.456 |
