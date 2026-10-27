# Amrutam Healthcare API

A FastAPI backend for patient registration and authentication, doctor discovery, appointment booking, consultations, and prescriptions.

## Tech stack

- Python and FastAPI
- SQLAlchemy ORM and Alembic migrations
- PostgreSQL with Psycopg 3
- JWT bearer authentication
- Argon2 password hashing
- Pytest and HTTPX for API tests

## Requirements

- Python version compatible with the pinned dependencies in `requirements.txt`
- PostgreSQL database
- Git

## Local setup (Windows PowerShell)

1. Create and activate a virtual environment:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Install dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

3. Create a local environment file from the example:

   ```powershell
   Copy-Item .env.example .env
   ```

4. Edit `.env` locally and set a real PostgreSQL URL and a unique random JWT secret of at least 32 bytes. The example secret is deliberately rejected by the application until you replace it. Never commit `.env` or share credentials in chat.

   ```env
   DATABASE_URL=postgresql+psycopg://USERNAME:PASSWORD@HOST:5432/DATABASE
   JWT_SECRET_KEY=REPLACE_WITH_A_UNIQUE_RANDOM_SECRET_OF_AT_LEAST_32_BYTES
   JWT_ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   ```

5. Initialize or migrate the database using the correct path below. **Back up existing data and verify the database URL before running any migration. Do not use a production database for first-time migration experiments.**

   **Brand-new, empty database only:** create an empty PostgreSQL database and run the migration chain:

   ```powershell
   alembic upgrade head
   alembic current
   ```

   **Existing database with the application's tables:** inspect the current revision, then run the migration chain:

   ```powershell
   alembic current
   alembic upgrade head
   alembic current
   ```

   The baseline migration creates the schema only when none of the application's tables exist. It preserves a complete existing application schema, and the doctor-link migration adds missing doctor-account linkage without recreating existing columns, indexes, or foreign keys. A partially populated application schema causes the baseline to stop with an explicit error. Do not bypass that error with `stamp`; investigate and reconcile the schema with a backup first.

6. Start the API from the project root:

   ```powershell
   python -m uvicorn main:app --reload
   ```

7. Open Swagger UI at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs). This local URL is only reachable from your computer unless the service is deployed.

## Environment variables

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | SQLAlchemy PostgreSQL connection URL |
| `JWT_SECRET_KEY` | Secret used to sign JWT access tokens |
| `JWT_ALGORITHM` | JWT signing algorithm (defaults to HS256) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access-token lifetime (defaults to 30) |

## API overview

| Area | Endpoints |
| --- | --- |
| Health | `GET /`, `GET /health/live` (process liveness), `GET /health` and `GET /health/ready` (database readiness) |
| Authentication | `POST /auth/register`, `POST /auth/login`, `GET /auth/me` |
| Doctors | `GET /doctors/`, `GET /doctors/{doctor_id}`, `POST /doctors/` (admin only) |
| Appointments | `POST /appointments/`, `GET /appointments/me` (patient's or assigned doctor's appointments), `GET /appointments/{appointment_id}` (owner/assigned doctor only), `POST /appointments/{appointment_id}/cancel` (patient only) |
| Consultations | `POST /consultations/`, `GET /consultations/me`, `PATCH /consultations/{consultation_id}` (assigned doctor, before finalization), `POST /consultations/{consultation_id}/complete` |
| Prescriptions | `POST /prescriptions/`, `GET /prescriptions/me` |

Use the Swagger `Authorize` control with a bearer access token for protected endpoints. Public registration creates patient accounts; doctor/admin provisioning should be handled through a trusted administrative process.

## Tests

Run the automated tests from the project root:

```powershell
python -m pytest -q
```

GitHub Actions runs the same test suite on pushes to `main` and `fix/**` branches and on pull requests targeting `main`. The suite includes isolated SQLite-backed API tests for authentication, validation, role-scoped appointment access, consultation finalization, prescription access, idempotency, database-readiness failure handling, and fresh/existing/partial schema migration paths. These tests do not connect to or modify a production database.

## Security notes

- Keep `.env`, access tokens, passwords, database credentials, and production secrets out of Git.
- Use a unique strong JWT secret in each environment.
- Use HTTPS when deployed.
- Provision doctor and administrator accounts through controlled, audited processes.
- Use synthetic data and test-only prescription text when testing; never treat test prescriptions as medical advice.
