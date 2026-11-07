// Closed-loop load test: each VU sends a query, waits for the answer, repeats.
// MODE=rerank|hybrid|vector|keyword  VUS=10  DURATION=30s  BASE_URL=http://localhost:8000
import http from "k6/http";
import { check } from "k6";

const queries = open("../eval/queries.jsonl")
  .split("\n")
  .filter((line) => line.trim())
  .map((line) => JSON.parse(line).query);

const MODE = __ENV.MODE || "rerank";
const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";

export const options = {
  vus: Number(__ENV.VUS || 10),
  duration: __ENV.DURATION || "30s",
  summaryTrendStats: ["avg", "p(50)", "p(95)", "p(99)", "max"],
  thresholds: { http_req_failed: ["rate<0.01"] },
};

export default function () {
  const q = queries[Math.floor(Math.random() * queries.length)];
  const res = http.get(`${BASE_URL}/search?q=${encodeURIComponent(q)}&mode=${MODE}&k=10`, {
    tags: { mode: MODE },
  });
  check(res, { "status 200": (r) => r.status === 200 });
}
