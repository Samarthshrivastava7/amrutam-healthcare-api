import http from "k6";
import { check, sleep } from "k6";

// Low-volume health smoke test only. This does not establish business API
// capacity or assignment performance targets.
const baseUrl = __ENV.BASE_URL || "http://127.0.0.1:8000";

export const options = {
  vus: 2,
  duration: "30s",
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<500"],
  },
};

export default function () {
  const live = http.get(`${baseUrl}/health/live`);
  check(live, { "liveness returns 200": (r) => r.status === 200 });

  const ready = http.get(`${baseUrl}/health/ready`);
  check(ready, { "readiness returns 200": (r) => r.status === 200 });
  sleep(1);
}
