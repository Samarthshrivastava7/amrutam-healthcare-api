# Observability Plan

## Current baseline

The API exposes process liveness at GET /health/live and database readiness at GET /health/ready (also GET /health). These are health probes, not a complete observability stack. The repository does not yet prove that a metrics backend, trace collector, dashboards or paging alerts are deployed.

## Signals to collect

### Metrics

- Request rate, duration histogram and response status class by route template/method.
- 5xx rate and request timeouts.
- SQLAlchemy pool checked-out connections, pool timeouts and DB query latency.
- Process CPU, memory, restarts and container health.
- Database CPU, connection utilization, storage, and backup health from the database provider.
- Booking conflicts and idempotency replays as aggregate counters without patient identifiers.

### Structured logs

Use JSON logs with timestamp, severity, service, environment, version/commit, route template, HTTP method/status, duration, and a generated request/correlation ID. Redact Authorization/Cookie headers. Never log passwords, JWTs, raw request bodies, consultation notes, prescription text, email addresses or direct identifiers. Configure bounded retention and access control.

### Traces

Propagate W3C trace context through the edge and API. Instrument request handling and database spans using OpenTelemetry, and export to an OTLP-compatible collector. Apply sampling to control volume, while retaining error traces according to policy. Do not attach clinical content or identifiers to span attributes.

## Suggested initial alerts

| Alert | Starting condition | Response |
|---|---|---|
| API error rate | 5xx > 2% for 5 minutes with meaningful traffic | Check release, DB readiness and dependency errors |
| Readiness failure | Any instance unhealthy for 2 minutes | Check database and pool; replace unhealthy instance |
| Latency | Read p95 > 200 ms or write p95 > 500 ms for 10 minutes | Inspect pool, query plans and saturation |
| Saturation | DB connections > 80% of configured maximum for 10 minutes | Check pool sizing and leaked sessions before scaling |
| Backup failure | Provider reports failed or overdue backup | Escalate and verify recovery path |
| Authentication abuse | Sustained failed-login spike | Apply rate limits and review safe security metadata |

These are proposed thresholds, not active alerts or a guarantee of SLO compliance. Tune them against traffic and false-positive rates.

## Privacy-safe dimensions

Allowed metric labels: bounded route template, HTTP method, status class and deployment environment. Never label metrics with patient/user IDs, email, appointment IDs, free-text query values, or clinical details. Avoid raw URL paths containing object IDs as metric labels.

## SLO validation

Assignment targets are read p95 < 200 ms, write p95 < 500 ms, 99.95% availability and 100,000 consultations/day. Use authorized representative load tests and record environment, dataset size, p50/p95/p99, throughput, errors and resource saturation. The included k6 script is only a liveness smoke test and cannot prove these targets.


## Current CI and smoke-test status

The repository now includes PostgreSQL concurrency tests in GitHub Actions and a dependency/secret scanning workflow. A k6 health smoke script exists, but no successful k6 execution, external metrics backend, trace collector, dashboard or paging alert has been verified here. Do not describe the proposed alert thresholds as active production alerts.


## Implemented telemetry baseline

The API now includes Prometheus request count and duration metrics with bounded labels (method, route template and status class). The /metrics endpoint is disabled unless METRICS_BEARER_TOKEN is configured and then requires bearer authentication. Metrics are process-local and need an external scraper/backend to aggregate across instances. No dashboard, alert delivery, trace collector or external monitoring service is deployed by these repository changes. See [production hardening runbook](production-hardening.md).

The application can optionally enforce TRUSTED_HOSTS, HTTPS_REDIRECT and CORS_ORIGINS. These are not enabled automatically in the live environment; configure and verify them in hosting settings before claiming the corresponding control is active. The repository does not yet implement distributed rate limiting or MFA.
