# Five-Minute Demo Script — Amrutam Healthcare API

**Safety:** Use synthetic accounts and fictional clinical details only. Do not show real patient data, passwords, access tokens, database URLs or secrets. Record only after CI passes and the API/database are verified.

## 0:00–0:30 — Overview
- Introduce FastAPI, SQLAlchemy, PostgreSQL, Alembic, JWT, Argon2, pytest and GitHub Actions.
- State this is an assignment implementation; do not claim certification or unmeasured scale targets.

## 0:30–1:15 — Authentication and roles
- Open Swagger UI at `/docs`.
- Register a synthetic patient, log in, and call `GET /auth/me` using Swagger Authorize.
- Explain public registration always assigns the patient role.

## 1:15–2:00 — Doctor discovery and availability
- Show active doctor discovery and specialization filtering.
- Authenticate as a provisioned synthetic doctor and publish a future timezone-aware slot.
- List the slot and show that an overlapping window is rejected.

## 2:00–3:00 — Booking workflow
- Authenticate as the synthetic patient and book the slot.
- Replay the same request with the same idempotency key.
- Attempt a conflicting booking and show the conflict response.
- Cancel the booking and show its updated status.

## 3:00–3:45 — Consultation, prescription and admin
- Authenticate as the assigned doctor and demonstrate the allowed consultation lifecycle.
- Create a fictional prescription record.
- As an admin, call `GET /admin/analytics/overview`; show that a patient token is denied.

## 3:45–4:30 — Engineering quality
- Show architecture/ER/sequence diagrams.
- Show GitHub Actions for Python 3.12/3.13, PostgreSQL concurrency tests, dependency audit and secret scanning.
- Show liveness/readiness endpoints and privacy-safe request IDs.

## 4:30–5:00 — Honest close
- Summarize implemented scope and safeguards.
- Clarify that 100,000 consultations/day, p95 latency objectives and 99.95% availability are not proven by a smoke test.
- Note remaining production hardening: MFA, distributed rate limiting, full audit coverage, telemetry and verified backup/restore.
