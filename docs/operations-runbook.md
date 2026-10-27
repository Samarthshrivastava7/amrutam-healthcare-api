# Operations Runbook

## Environments and secrets

- Use a distinct database and JWT secret for local, CI, staging and production.
- Store secrets in the platform secret manager; do not commit .env.
- Set DATABASE_URL, JWT_SECRET_KEY (at least 32 random bytes), JWT_ALGORITHM=HS256, and ACCESS_TOKEN_EXPIRE_MINUTES.
- Do not use real patient data in local or demo environments.

## Local Docker Compose

1. Set local-only POSTGRES_PASSWORD and JWT_SECRET_KEY environment variables using strong unique values. Compose also accepts POSTGRES_DB, POSTGRES_USER and API_PORT.
2. Start the database: docker compose up -d db.
3. Wait for docker compose ps to show the database healthy.
4. Apply migrations as an explicit one-off task: docker compose run --rm api alembic upgrade head. If the API image cannot start because configuration is incomplete, verify Compose variables and rebuild. Do not bypass migration errors with stamp.
5. Start the API: docker compose up -d api.
6. Verify GET /health/live, GET /health/ready and /docs from a trusted development machine.
7. View logs with docker compose logs --tail=200 api db.

This Compose stack is for local development/integration checks, not high availability. Do not expose PostgreSQL publicly.

## Release checklist

- [ ] Review diff and confirm no credentials, tokens, personal data or database dumps are committed.
- [ ] Dependency scan, syntax/format checks and complete tests pass.
- [ ] Back up the target database and verify the restore path before schema changes.
- [ ] Apply backward-compatible migrations as a separate job.
- [ ] Deploy an immutable commit/image reference.
- [ ] Verify readiness and run smoke tests using synthetic accounts.
- [ ] Monitor 4xx/5xx rates, latency percentiles, DB connections, CPU/memory and logs.
- [ ] Roll back the application image where safe; use a forward fix for irreversible schema/data changes.

## Incident triage

| Signal | First checks | Safe response |
|---|---|---|
| Liveness fails | Process exit, deployment events, resource exhaustion | Replace instance and inspect logs without exposing secrets |
| Readiness returns 503 | DB availability, network, credentials, connection limits | Check DB status and pool saturation; never print connection string |
| Increased 401 | Expired token, client clock, JWT config mismatch | Confirm environment/expiry; never ask for tokens |
| Increased 403/404 | Role, active status, doctor link, ownership | Verify authorization with synthetic records; do not weaken controls |
| Increased 409 on booking | Idempotency key, time conflict, concurrency | Inspect safe metadata; do not retry with a new key blindly |
| High p95/p99 | Pool wait, query plans, CPU/memory, downstream calls | Capture metrics and query plans before scaling |
| Suspected clinical-data exposure | Access logs and affected routes/identities | Restrict access, preserve evidence, rotate affected credentials and follow incident policy |

## Backup and recovery

Configure encrypted managed backups and point-in-time recovery where available. Restrict backup operators, monitor backup success, and record retention settings. Restore into an isolated environment on a schedule and after major database changes. Record actual recovery point and recovery time. Proposed design objectives are RPO <= 15 minutes and RTO <= 4 hours; do not claim these targets until a restore exercise demonstrates them.

## Secret rotation

1. Create a new random JWT key through the secret manager.
2. Plan a controlled deployment window because the current single-key JWT validation invalidates tokens signed with the old key.
3. Deploy the new key to all instances and verify login and authenticated smoke tests.
4. Revoke or expire outstanding sessions according to incident severity.
5. Rotate database credentials independently and verify connection pools reconnect.
6. Never paste secrets or bearer tokens into issues, logs, screenshots or chat.
