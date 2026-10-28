# Production Security, Monitoring and Load-Test Runbook

This is an implementation and rollout checklist, not a production certification. Code-level controls do not replace managed platform controls, a security review, or a verified test against the actual deployment.

## Implemented in this branch

- Baseline response headers: request ID, nosniff, frame denial, no-referrer, no-store and a restrictive Permissions-Policy.
- Optional trusted-host validation via TRUSTED_HOSTS.
- Optional HTTPS redirect via HTTPS_REDIRECT=true; enable only when the hosting platform correctly terminates TLS and forwards requests securely.
- Optional explicit CORS origin allowlist via CORS_ORIGINS; do not use wildcard origins with credentials.
- Prometheus request counter and request-duration histogram labelled only by method, route template and status class.
- /metrics is hidden from OpenAPI and disabled (404) unless METRICS_BEARER_TOKEN is set; it requires a bearer token when enabled.
- Tests for metrics access control and a bounded k6 staging load profile.

## Deployment configuration

Configure these through the hosting platform's secret/environment settings, not a committed .env:

- TRUSTED_HOSTS=amrutam-healthcare-api.onrender.com plus any verified custom API hostnames. Values are hostnames only; no scheme or port.
- HTTPS_REDIRECT=true only after confirming the proxy terminates TLS and the app receives the correct scheme/forwarded-header configuration. If redirect loops occur, disable and configure the trusted proxy correctly before re-enabling.
- CORS_ORIGINS=https://your-verified-frontend.example using the exact frontend origin(s). Remove unused origins.
- METRICS_BEARER_TOKEN: generate a long random secret and store it only in the platform secret manager. Grant it only to the monitoring scraper. If the platform cannot safely protect this endpoint, leave the token unset (metrics endpoint stays disabled) and collect metrics through the host/provider instead.
- Keep database ingress private/restricted, use a least-privilege database user, TLS database connections where supported, and managed secret rotation.

Do not enable a host allowlist until every intended API hostname is known. Do not use the public deployment for unapproved stress tests.

## Rate limiting and abuse controls

Application-level per-process memory limits are not sufficient for multi-instance deployments. Configure shared edge/gateway rate limits before production:
- Login: start conservatively (for example, 5 failed attempts per account/IP per minute) with an account-aware strategy that does not enable easy lockout attacks.
- Registration: apply per-IP and abuse/bot protection.
- API-wide: cap request body size, concurrent requests and upstream timeouts.
- Use a shared/distributed limiter if limits must be enforced across replicas. Do not trust arbitrary client-supplied forwarded IP headers; only trust headers set by the known reverse proxy.
- Alert on sustained authentication failures and 429 spikes. Avoid logging passwords, tokens, raw bodies, email addresses or clinical content.

These are deployment requirements; this repository does not implement a distributed rate limiter or MFA.

## Metrics and alerts

Scrape /metrics only over a private path/network with the bearer token held by the scraper. Metrics are process-local, so aggregate across replicas in the monitoring backend. Do not attach patient identifiers, appointment IDs, emails, query strings or clinical content to metric labels.

Recommended initial alerts to tune after observing normal traffic:
- 5xx rate > 2% for 5 minutes with meaningful traffic.
- Readiness failures for 2 minutes.
- Read p95 > 200 ms or write p95 > 500 ms for 10 minutes.
- Database connection usage > 80% of configured maximum for 10 minutes.
- Authentication failures or 429 rate materially above baseline.
- Managed backup failures or overdue backups.

The code emits metrics but does not deploy Prometheus, Grafana, an OTLP collector, dashboards, or paging alerts. Configure those in the chosen hosting/monitoring platform and test the notification path.

## Authorized load-test procedure

1. Prefer a local disposable environment or staging environment with synthetic data.
2. Confirm the environment owner approved the test window and the target URL.
3. Start the API and database; verify /health/live and /health/ready.
4. Install k6 from its official distribution.
5. Run the existing low-volume liveness smoke test: k6 run tests/load/k6-smoke.js
6. Run the bounded readiness test: BASE_URL=http://127.0.0.1:8000 TARGET_VUS=20 k6 run tests/load/k6-load.js. On PowerShell, set $env:BASE_URL and $env:TARGET_VUS before invoking k6.
7. Record commit, deployment size, DB tier, data volume, VUs, duration, throughput, p50/p95/p99, failure rate, CPU/memory and DB connections.
8. Stop immediately if errors, saturation, elevated costs or user impact appear. Do not test against production without an explicit change window and rollback/stop plan.

This readiness-only profile validates the HTTP/DB health path, not the booking write path or 100,000-consultations/day capacity target. A representative capacity test requires seeded synthetic data and controlled authenticated read/write scenarios. Do not claim the stated SLOs until results from the actual target architecture support them.

## Remaining production gates

- [ ] Shared edge/distributed rate limiting and body-size limits configured.
- [ ] Privileged MFA and complete clinical audit coverage.
- [ ] TLS, hostname and CORS settings verified in the live host.
- [ ] Metrics scraper, dashboard, alert rules and notification route configured and tested.
- [ ] Dependency/security scans and full CI pass on the release commit.
- [ ] Encrypted backups and an isolated restore drill verified.
- [ ] Staging load test covers representative authenticated reads and writes.
- [ ] Performance and availability SLOs measured; incident/rollback procedures rehearsed.
