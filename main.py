import hmac
import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.routes.admin_analytics import router as admin_analytics_router
from app.api.routes.auth import router as auth_router
from app.api.routes.doctors import router as doctors_router
from app.api.routes.appointments import router as appointments_router
from app.api.routes.consultations import router as consultations_router
from app.api.routes.prescriptions import router as prescriptions_router
from app.db.session import get_db

logger = logging.getLogger("amrutam.access")
REQUESTS = Counter(
    "amrutam_http_requests_total",
    "HTTP requests handled by the API",
    ("method", "route", "status_class"),
)
REQUEST_DURATION = Histogram(
    "amrutam_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ("method", "route"),
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.2, 0.3, 0.5, 1, 2.5, 5, 10),
)
METRICS_BEARER_TOKEN = os.getenv("METRICS_BEARER_TOKEN", "").strip()

app = FastAPI(
    title="Amrutam Healthcare API",
    description="Backend API for doctor appointments and healthcare consultations",
    version="1.2.0",
)

# Configure these at the hosting platform. Empty values preserve local development defaults.
trusted_hosts = [host.strip() for host in os.getenv("TRUSTED_HOSTS", "").split(",") if host.strip()]
if trusted_hosts:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=trusted_hosts)

if os.getenv("HTTPS_REDIRECT", "false").strip().lower() in {"1", "true", "yes"}:
    app.add_middleware(HTTPSRedirectMiddleware)

cors_origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "").split(",") if origin.strip()]
if cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Request-ID"],
    )

app.include_router(auth_router)
app.include_router(admin_analytics_router)
app.include_router(doctors_router)
app.include_router(appointments_router)
app.include_router(consultations_router)
app.include_router(prescriptions_router)


@app.middleware("http")
async def request_observability(request: Request, call_next):
    """Emit privacy-safe structured logs, metrics and baseline security headers."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    started = time.perf_counter()
    status_code = 500
    response = None

    try:
        response = await call_next(request)
        status_code = response.status_code
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response
    finally:
        route = request.scope.get("route")
        route_template = getattr(route, "path", "<unmatched>")
        duration_seconds = time.perf_counter() - started
        duration_ms = round(duration_seconds * 1000, 2)
        status_class = f"{status_code // 100}xx"
        REQUESTS.labels(request.method, route_template, status_class).inc()
        REQUEST_DURATION.labels(request.method, route_template).observe(duration_seconds)
        # Never log query strings, client IDs, headers, bodies, users, tokens or clinical data.
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


@app.get("/metrics", include_in_schema=False)
def metrics(request: Request):
    """Prometheus metrics; disabled unless a bearer token is configured."""
    if not METRICS_BEARER_TOKEN:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    authorization = request.headers.get("authorization", "")
    scheme, _, supplied = authorization.partition(" ")
    if scheme.lower() != "bearer" or not hmac.compare_digest(supplied, METRICS_BEARER_TOKEN):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Metrics authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


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
