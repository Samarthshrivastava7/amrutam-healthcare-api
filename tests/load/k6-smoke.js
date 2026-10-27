// Synthetic smoke traffic only. Never run against production without explicit authorization.
import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";

const errors = new Rate("http_errors");
const readLatency = new Trend("health_read_latency", true);
const baseUrl = __ENV.BASE_URL || "http://127.0.0.1:8000";

export const options = {
  stages: [
    { duration: "30s", target: 5 },
    { duration: "1m", target: 10 },
    { duration: "30s", target: 0 },
  ],
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<200"],
    http_errors: ["rate<0.01"],
  },
};

export default function () {
  const response = http.get(`${baseUrl}/health/live`, { tags: { endpoint: "liveness" } });
  readLatency.add(response.timings.duration);
  const ok = check(response, {
    "liveness returns 200": (r) => r.status === 200,
    "liveness body is healthy": (r) => r.json("status") === "healthy",
  });
  errors.add(!ok);
  sleep(1);
}
