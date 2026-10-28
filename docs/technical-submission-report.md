# Amrutam Healthcare API — Technical Submission Report

**Project:** Amrutam Healthcare API  
**Repository:** https://github.com/Samarthshrivastava7/amrutam-healthcare-api  
**Live API:** https://amrutam-healthcare-api.onrender.com  
**Swagger / OpenAPI UI:** https://amrutam-healthcare-api.onrender.com/docs  
**Readiness probe:** https://amrutam-healthcare-api.onrender.com/health/ready

## 1. Executive summary

This repository contains an assignment-scale REST API for patient authentication, doctor discovery, availability publishing, appointment booking/cancellation, consultations and prescriptions. It uses FastAPI, SQLAlchemy, PostgreSQL, Alembic, JWT bearer authentication, Argon2 password hashing, Pytest, Docker Compose and GitHub Actions.

The codebase includes architecture/design documents, an ER diagram, a booking-sequence diagram, a security threat model, observability guidance, an operations runbook, a demo script and PostgreSQL concurrency tests.

**Scope statement:** this is a substantial assignment implementation, not a production-certified healthcare platform. Items listed as pending below must not be represented as implemented or verified.

## 2. Architecture

- **HTTP/API layer:** FastAPI routes with typed Pydantic request/response schemas and generated OpenAPI documentation.
- **Identity and access:** patient registration/login, expiring JWT access tokens, Argon2 password hashing, role checks and resource ownership checks.
- **Domain layer:** doctor profiles, published availability, appointments, consultation lifecycle and prescriptions.
- **Persistence:** SQLAlchemy ORM over PostgreSQL; Alembic manages schema changes.
- **Quality gates:** pytest, SQLite-backed route tests, dedicated PostgreSQL concurrency tests, dependency/security workflows and GitHub Actions.
- **Deployment:** Render-hosted API with a managed PostgreSQL connection configured outside the repository; Docker Compose supports local development.

Detailed diagrams and design rationale are in [architecture.md](architecture.md), [high-level-architecture.mmd](high-level-architecture.mmd), [er-diagram.mmd](er-diagram.mmd), [booking-sequence.mmd](booking-sequence.mmd) and [design-decisions.md](design-decisions.md).

## 3. Functional scope

| Capability | Current status | Notes |
|---|---|---|
| Patient registration and login | Implemented | Registration always assigns patient role; duplicate email returns conflict |
| Current-user endpoint | Implemented | Requires valid bearer token |
| Doctor discovery | Implemented | Active doctor listing/filtering |
| Privileged doctor provisioning | Implemented | Operator/admin-controlled; not public self-registration |
| Doctor availability | Implemented | Future windows and overlap validation |
| Appointment booking/cancellation | Implemented | Published slot checks, ownership checks and idempotency handling |
| Consultation workflow | Implemented | Assigned-doctor access and lifecycle endpoints |
| Prescriptions | Implemented | Creation/retrieval routes with authorization |
| Admin overview analytics | Implemented | Admin-only aggregate endpoint |
| Health endpoints | Implemented | Liveness and DB readiness probes |
| Schema migrations | Implemented | Alembic migration chain and dedicated workflow |
| Payment workflow | Not implemented | No payment provider or payment state machine |
| Self-service password reset | Not implemented | No email/token reset flow |
| Privileged MFA | Not implemented | Requires a separate identity/control design |
| Distributed rate limiting | Not implemented | Should be enforced at a shared edge or distributed store |
| Complete clinical audit coverage | Partial | Authentication and appointment metadata events exist; all clinical reads/mutations are not covered |
| Production telemetry/alerting | Not verified/configured | Guidance exists; no deployed metrics/tracing/alerting backend is claimed |

## 4. Security and privacy controls

Implemented controls include password hashing, expiring JWTs, startup validation for the signing key, generic login errors, fixed patient role at public registration, role-scoped authorization, typed schemas, privacy-conscious access logging, generated request IDs and basic response hardening headers.

Before real patient data or production use, complete the checklist in [threat-model.md](threat-model.md). In particular:
- rotate any database/JWT credentials that may have been exposed and store secrets only in the hosting provider's secret settings;
- enforce TLS and appropriate trusted-host/CORS settings at the deployment boundary;
- add login/registration abuse controls and MFA for privileged accounts;
- complete auditable clinical access/mutation events;
- establish retention, incident-response, encrypted-backup and tested-restore procedures;
- conduct qualified privacy/security review and authorized penetration testing.

Use synthetic patient and clinical data for demos. Do not commit .env files, tokens, credentials, database dumps or real clinical records.

## 5. Testing and CI

The repository's GitHub Actions configuration includes a Python 3.12/3.13 test matrix, dependency consistency checking, compilation, automated tests, a PostgreSQL service for concurrency tests, and a separate security/dependency workflow. A database migration workflow is also present.

Recent verified runs at the time of preparing this report:
- [Tests / Security run 40649289243](https://github.com/Samarthshrivastava7/amrutam-healthcare-api/actions/runs/40649289243)
- [Security run 40649289477](https://github.com/Samarthshrivastava7/amrutam-healthcare-api/actions/runs/40649289477)
- [Database migration run 40650477661](https://github.com/Samarthshrivastava7/amrutam-healthcare-api/actions/runs/40650477661)

Re-check the latest workflow status after any new commit; the historical successes above do not guarantee that a future commit passes.

Run locally from the repository root:

```bash
python -m pip install -r requirements.txt
python -m pytest -q
```

The included [k6 smoke script](../tests/load/k6-smoke.js) checks health endpoints under synthetic traffic only. It is not a capacity benchmark.

## 6. Deployment and API exploration

1. Open the [Swagger UI](https://amrutam-healthcare-api.onrender.com/docs).
2. Check [liveness](https://amrutam-healthcare-api.onrender.com/health/live) and [database readiness](https://amrutam-healthcare-api.onrender.com/health/ready).
3. Register a synthetic patient and log in.
4. Use Swagger's **Authorize** control with the returned bearer token.
5. Demonstrate doctor discovery, availability, booking/cancellation, and authorized consultation/prescription workflows using pre-provisioned synthetic doctor/admin accounts.
6. Show a negative authorization test: a patient must not be able to create doctor profiles or read another patient's records.

A public registration token is a patient token. Doctor/admin credentials must be provisioned through a trusted operator process. Do not expose tokens or secrets in a screen recording.

## 7. Performance and reliability claims

The assignment's aspirational goals include 100,000 consultations/day, read p95 below 200 ms, write p95 below 500 ms and 99.95% availability. These targets have **not** been established by the health smoke test or current CI alone. Validate them with a representative, authorized PostgreSQL load test, production-like data volumes, resource monitoring and a defined observation window.

A production release also requires verified TLS/host configuration, operational alerting, managed secret rotation, and a successful backup/restore drill. The [observability plan](observability.md) and [operations runbook](operations-runbook.md) describe the required work but do not claim it has already been performed.

## 8. Demo checklist

Use the sequence in [demo-script.md](demo-script.md), and keep the recording to approximately five minutes:
- overview and architecture;
- synthetic patient registration/login/current-user;
- doctor discovery and published availability;
- appointment booking, idempotent replay, conflict and cancellation;
- assigned-doctor consultation and fictional prescription;
- admin authorization check;
- GitHub Actions, migrations, diagrams and health endpoints;
- brief honest statement of remaining production gaps.

## 9. Final assessment

The repository provides a working assignment-scale healthcare API foundation with meaningful authorization, database migrations, tests, CI and engineering documentation. It should be submitted with the source repository, live API/Swagger links, this report, and a separately recorded five-minute demo if the evaluator explicitly requires a video.

It should **not** be described as production-ready or compliant until the outstanding security, operational, privacy and performance controls have been implemented and verified.
