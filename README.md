# Amrutam Healthcare API

A modular FastAPI backend for patient identity, doctor discovery, appointment booking, consultations and prescriptions. The repository emphasizes explicit authorization, idempotent writes, repeatable local setup, migration safety and honest documentation of production gaps.

## Technology

- Python 3.13 / FastAPI
- SQLAlchemy ORM and Alembic migrations
- PostgreSQL with Psycopg 3
- JWT bearer authentication and Argon2 password hashing
- Pydantic request/response schemas
- Pytest API tests and GitHub Actions CI
- Docker / Docker Compose for reproducible local infrastructure

## Current capabilities

- Patient registration, login and current-user endpoint
- Admin-controlled doctor profile creation and public active-doctor discovery/filtering
- Doctor-owned future availability windows, overlap validation, and public time-window discovery
- Booking validation against published slot start times once a doctor has configured availability
- Patient appointment booking/cancellation and patient/assigned-doctor record access
- Idempotency-key replay handling for appointment writes
- Assigned-doctor consultation lifecycle and prescription creation/retrieval
- Liveness and database-readiness endpoints

Public registration always creates a patient. Doctor/admin accounts must be provisioned through a trusted operator workflow. Use only synthetic patient data for local tests and demos.

## Local setup — Windows PowerShell

1. Create and activate a virtual environment:

   py -m venv .venv
   .\.venv\Scripts\Activate.ps1

2. Install dependencies:

   python -m pip install -r requirements.txt

3. Create the local environment file:

   Copy-Item .env.example .env

4. Edit .env with a PostgreSQL URL and a unique random JWT secret of at least 32 bytes. Never commit .env or share credentials/tokens in chat.

   DATABASE_URL=postgresql+psycopg://USERNAME:PASSWORD@HOST:5432/DATABASE
   JWT_SECRET_KEY=REPLACE_WITH_A_UNIQUE_RANDOM_SECRET_OF_AT_LEAST_32_BYTES
   JWT_ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=30

5. Back up any existing database and verify DATABASE_URL before migrations. Never use a production database for setup experiments.

   For a brand-new empty database: run alembic upgrade head, then alembic current.
   For an existing application database: inspect alembic current, run alembic upgrade head, and inspect alembic current again.

   The migration chain is designed to avoid recreating an existing complete schema. A partial schema causes an explicit error; do not bypass it with alembic stamp. Investigate and reconcile the schema using a backup first.

6. Start the local API:

   python -m uvicorn main:app --reload

7. Open Swagger UI at http://127.0.0.1:8000/docs. The URL is local to your machine unless the API is deployed.

## Docker Compose

Docker Compose runs a PostgreSQL container and the API on a private bridge network. It is intended for local development/integration testing, not high availability.

1. Install Docker Desktop and start its engine.
2. Set POSTGRES_PASSWORD and JWT_SECRET_KEY in your shell to strong, unique local values. Optional variables are POSTGRES_DB, POSTGRES_USER and API_PORT.
3. Start the database with docker compose up -d db.
4. Run the schema migration explicitly with docker compose run --rm api alembic upgrade head.
5. Start the API with docker compose up -d api.
6. Check http://127.0.0.1:8000/health/ready and http://127.0.0.1:8000/docs.
7. Inspect logs with docker compose logs --tail=200 api db.

Do not expose PostgreSQL publicly. Back up and verify the target database before migrations. Migrations intentionally do not run automatically on every web-worker startup.

## Environment variables

| Variable | Purpose |
|---|---|
| DATABASE_URL | SQLAlchemy PostgreSQL connection URL |
| JWT_SECRET_KEY | Unique secret for signing JWT access tokens; at least 32 bytes |
| JWT_ALGORITHM | HMAC algorithm; defaults to HS256 |
| ACCESS_TOKEN_EXPIRE_MINUTES | Access-token lifetime; defaults to 30 |
| POSTGRES_DB | Compose database name |
| POSTGRES_USER | Compose database user |
| POSTGRES_PASSWORD | Compose database password; required |
| API_PORT | Local host port; defaults to 8000 |

## API overview

| Area | Endpoints |
|---|---|
| Health | GET /, GET /health/live, GET /health/ready, GET /health |
| Authentication | POST /auth/register, POST /auth/login, GET /auth/me |
| Doctors | GET /doctors/, GET /doctors/{doctor_id}, POST /doctors/ (admin only), POST /doctors/me/availability (doctor), GET /doctors/{doctor_id}/availability |
| Appointments | POST /appointments/, GET /appointments/me, GET /appointments/{appointment_id}, POST /appointments/{appointment_id}/cancel |
| Admin analytics | GET /admin/analytics/overview (admin only) |
| Consultations | POST /consultations/, GET /consultations/me, PATCH /consultations/{consultation_id}, POST /consultations/{consultation_id}/complete |
| Prescriptions | POST /prescriptions/, GET /prescriptions/me |

Use Swagger's Authorize control with a bearer access token for protected endpoints. Do not share access tokens or screenshots containing them.

## Tests and CI

Run tests from the repository root:

    python -m pytest -q

GitHub Actions runs dependency consistency checks, Python compilation and the automated test suite on the configured Python matrix. Tests use isolated synthetic data and SQLite; they must not connect to production. SQLite tests do not prove PostgreSQL row-locking behavior, migration safety against all real schemas, or production load capacity.

A small k6 smoke script is provided at tests/load/k6-smoke.js. It only checks liveness under light synthetic traffic; it is not a full capacity benchmark. Run only against a local or explicitly authorized non-production environment:

    k6 run tests/load/k6-smoke.js

Override the target with BASE_URL when needed.

## Design and operations documents

- [Architecture and design](docs/architecture.md)
- [Security checklist and threat model](docs/threat-model.md)
- [Observability plan](docs/observability.md)
- [Operations runbook](docs/operations-runbook.md)
- [High-level architecture diagram](docs/high-level-architecture.mmd)
- [ER diagram for implemented core entities](docs/er-diagram.mmd)
- [Booking sequence diagram source](docs/booking-sequence.mmd)
- [Design decisions: retries, caching, concurrency, partitioning and DR](docs/design-decisions.md)
- [Render Blueprint starter](infra/render.yaml)

## Security and production readiness

Implemented controls include Argon2 password hashes, expiring JWTs, startup validation for token configuration, fixed patient role during public registration, admin-only doctor profile creation and aggregate analytics, role-scoped data access, metadata-only audit events for appointment booking/cancellation, typed schemas, and generic readiness errors.

Before real patient data or production use, complete and verify TLS/host restrictions, managed secret rotation, login/registration rate limiting, privileged-account MFA, audit coverage for authentication and all clinical-record mutations, retention policy, dependency/secret scanning, operational alerting, backup/restore drills, and PostgreSQL concurrency/load tests. Availability slots and aggregate admin analytics are implemented; payments, distributed rate limiting, full clinical audit coverage, and a configured production telemetry backend are not complete. The project does not claim regulatory compliance or a 99.95% availability guarantee.

## Demo safety

Use synthetic accounts and fake clinical content. Test prescriptions are demonstration data, not medical advice. Before recording the demo, remove tokens from terminal history/screenshots and avoid displaying secrets or real patient information.
