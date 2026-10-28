// Bounded load profile for a local or explicitly authorized staging environment only.
// Do not point this at production without a written change window and explicit approval.
import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";

const errors = new Rate("api_errors");
const latency = new Trend("api_read_latency", true);
const baseUrl = __ENV.BASE_URL || "http://127.0.0.1:8000";

export const options = {
  stages: [
    { duration: "30s", target: Number(__ENV.START_VUS || 5) },
    { duration: "1m", target: Number(__ENV.TARGET_VUS || 20) },
    { duration: "30s", target: 0 },
  ],
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<500", "p(99)<1000"],
    api_errors: ["rate<0.01"],
  },
};

export default function () {
  const response = http.get(baseUrl + "/health/ready", {
    timeout: "5s",
    tags: { endpoint: "readiness" },
  });
  latency.add(response.timings.duration);
  const ok = check(response, {
    "readiness responds 200": (r) => r.status === 200,
    "database readiness is healthy": (r) => r.json("database") === "connected",
  });
  errors.add(!ok);
  sleep(0.5);
}
