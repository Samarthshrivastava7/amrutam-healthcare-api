# Security Checklist & Threat Model

**Status:** Engineering checklist, not a certification or legal opinion. Use synthetic records for demonstrations. Obtain qualified privacy/security review before handling real patient data.

## Assets and trust boundaries

| Asset | Classification | Primary risk |
|---|---|---|
| Credentials and access tokens | Restricted | Account takeover |
| Patient identity and appointment metadata | Sensitive personal data | Unauthorized disclosure |
| Consultation notes and prescriptions | Highly sensitive clinical data | Unauthorized reading, alteration or loss |
| JWT signing key and database credentials | Secret | Authentication or database compromise |
| Audit and operational telemetry | Internal; may contain sensitive metadata | Data leakage or loss of forensic evidence |

Trust boundaries: public internet → TLS proxy/rate limits → FastAPI routes and authorization dependencies → SQLAlchemy → PostgreSQL. Deployment secrets and CI credentials form a separate administrative boundary.

## Threat scenarios and controls

| Threat | Impact | Current / planned mitigation | Verification |
|---|---|---|---|
| Credential stuffing | Account takeover | Generic login errors and Argon2 hashing exist; add distributed rate limiting and alerting | Abuse tests and alert review |
| Broken object-level authorization | Patient records exposed | Queries are scoped to the patient or linked active doctor; admin access is not implicitly granted | Negative tests with two patients and an unrelated doctor |
| Privilege escalation at registration | Attacker creates doctor/admin | Public registration fixes role to patient; privileged provisioning is operator-controlled | Assert submitted role cannot change persisted role |
| Token/key compromise | Impersonation | Expiring JWT and strong secret validation; use TLS and managed secret storage | Key rotation and expiry tests |
| SQL injection | Data access/modification | SQLAlchemy parameterized statements and typed request schemas | Dependency scanning and security tests |
| Duplicate/replayed booking | Duplicate records | Idempotency key and uniqueness constraint exist; exact-time checks are not a full scheduling engine | Concurrent PostgreSQL integration test |
| Booking race condition | Double booking | Row-lock attempt exists; validate actual PostgreSQL isolation and enforce slot claims in database | Parallel booking test on disposable PostgreSQL |
| Sensitive data in logs | Patient data leakage | Do not log passwords, tokens, request bodies, notes or prescription text | Inspect logs with synthetic canary values |
| Dependency compromise | Outage or data compromise | CI tests exist; add dependency vulnerability and secret scanning | CI security scan |
| Database loss | Clinical data unavailable | Encrypted managed backups and recovery process required | Documented restore drill |
| Denial of service | API outage/cost | Apply body-size and rate limits at edge; bound pools and timeouts | Authorized load test and monitoring |
| Malicious administrator | Bulk access/tampering | Least privilege, MFA for operator identity, immutable audit events | Access review and audit verification |

## OWASP-aligned checklist

- [x] Argon2 password hashing and expiring JWTs.
- [x] Public registration cannot select a privileged role.
- [x] Admin-only doctor profile creation and role-scoped record queries.
- [x] Typed request/response schemas and generic authentication errors.
- [ ] Login/registration rate limits at a shared gateway or distributed limiter.
- [ ] MFA for privileged/operator accounts and audited administrator access.
- [ ] Append-only audit events for clinical-record access, creation, amendment, completion and administrative changes.
- [ ] TLS-only deployment, strict trusted-host and CORS configuration where applicable.
- [ ] Managed secrets, key rotation, token revocation strategy and least-privilege DB credentials.
- [ ] Dependency vulnerability scan, static analysis and secret scanning in CI.
- [ ] Retention/deletion policy, incident-response runbook and access review.
- [ ] Encrypted backups, point-in-time recovery where supported, and tested restoration.
- [ ] External penetration test and privacy/compliance review before real patient use.

## Data-handling rules

1. Never commit .env files, database URLs with credentials, JWTs, private keys, or production exports.
2. Use synthetic patients, doctors, notes and prescription details in development and demos.
3. Do not put authorization headers, passwords, clinical text, email addresses or direct identifiers in logs or metric labels.
4. Restrict backup and telemetry access with least privilege, encryption and bounded retention.
5. Keep public doctor profiles separate from private clinical records.

## Residual risk and honest scope

This is an assignment backend, not a production-certified telemedicine platform. MFA, a public self-service password reset, distributed rate limiting, clinical audit logging, full doctor availability/overlap scheduling, payments, admin analytics, a configured production telemetry backend, and a verified backup/restore process must not be claimed as implemented unless separately built and tested.
