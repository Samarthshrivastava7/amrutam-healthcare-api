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

4. Edit `.env` locally and set a real PostgreSQL URL and a strong, unique JWT secret. Never commit `.env` or share credentials in chat.

   ```env
   DATABASE_URL=postgresql+psycopg://USERNAME:PASSWORD@HOST:5432/DATABASE
   JWT_SECRET_KEY=replace-with-a-long-random-secret
   JWT_ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   ```

5. Apply migrations only after confirming the target database and its current Alembic revision:

   ```powershell
   alembic current
   alembic upgrade head
   ```

   The first migration is a baseline for an existing schema and contains no table-creation operations. Do not run migrations against a database you have not backed up or verified.

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
| Health | `GET /`, `GET /health` |
| Authentication | `POST /auth/register`, `POST /auth/login`, `GET /auth/me` |
| Doctors | `GET /doctors/`, `GET /doctors/{doctor_id}`, `POST /doctors/` (admin only) |
| Appointments | `POST /appointments/`, `GET /appointments/me`, `GET /appointments/{appointment_id}`, `POST /appointments/{appointment_id}/cancel` |
| Consultations | `POST /consultations/`, `GET /consultations/me`, `POST /consultations/{consultation_id}/complete` |
| Prescriptions | `POST /prescriptions/`, `GET /prescriptions/me` |

Use the Swagger `Authorize` control with a bearer access token for protected endpoints. Public registration creates patient accounts; doctor/admin provisioning should be handled through a trusted administrative process.

## Tests

Run the automated tests from the project root:

```powershell
python -m pytest -q
```

## Security notes

- Keep `.env`, access tokens, passwords, database credentials, and production secrets out of Git.
- Use a unique strong JWT secret in each environment.
- Use HTTPS when deployed.
- Provision doctor and administrator accounts through controlled, audited processes.
- Use synthetic data and test-only prescription text when testing; never treat test prescriptions as medical advice.
