import json
import logging
import time
import uuid
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, Request, Response, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.routes.auth import router as auth_router
from app.api.routes.doctors import router as doctors_router
from app.api.routes.appointments import router as appointments_router
from app.api.routes.consultations import router as consultations_router
from app.api.routes.prescriptions import router as prescriptions_router
from app.db.session import get_db

logger = logging.getLogger("amrutam.access")

app = FastAPI(
    title="Amrutam Healthcare API",
    description="Backend API for doctor appointments and healthcare consultations",
    version="1.1.0",
)

app.include_router(auth_router)
app.include_router(doctors_router)
app.include_router(appointments_router)
app.include_router(consultations_router)
app.include_router(prescriptions_router)


@app.middleware("http")
async def request_observability(request: Request, call_next):
    """Emit privacy-safe structured request logs and basic hardening headers."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    started = time.perf_counter()
    status_code = 500

    try:
        response = await call_next(request)
        status_code = response.status_code
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response
    finally:
        route = request.scope.get("route")
        route_template = getattr(route, "path", "<unmatched>")
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        # Deliberately omit query strings, client-supplied IDs, headers, body,
        # user identifiers, tokens, and clinical content from access logs.
        logger.info(
            json.dumps(
                {
                    "event": "http_request",
                    "request_id": request_id,
                    "method": request.method,
                    "route": route_template,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                },
                separators=(",", ":"),
                sort_keys=True,
            )
        )


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


@app.get("/", tags=["Health"])
def home():
    return {
        "message": "Amrutam Healthcare API is running",
        "status": "success",
    }


@app.get("/health/live", tags=["Health"])
def liveness_check():
    """Lightweight process check; deliberately does not require the database."""
    return {
        "status": "healthy",
        "service": "amrutam-backend",
        "timestamp": _timestamp(),
    }


@app.get("/health", tags=["Health"])
@app.get("/health/ready", tags=["Health"])
def readiness_check(
    response: Response,
    db: Session = Depends(get_db),
):
    """Readiness check that only reports healthy when the database responds."""
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "unavailable",
            "service": "amrutam-backend",
            "database": "unavailable",
            "timestamp": _timestamp(),
        }

    return {
        "status": "healthy",
        "service": "amrutam-backend",
        "database": "connected",
        "timestamp": _timestamp(),
    }
