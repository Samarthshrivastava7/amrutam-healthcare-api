from datetime import datetime, timezone

from fastapi import Depends, FastAPI, Response, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.routes.auth import router as auth_router
from app.api.routes.doctors import router as doctors_router
from app.api.routes.appointments import router as appointments_router
from app.api.routes.consultations import router as consultations_router
from app.api.routes.prescriptions import router as prescriptions_router
from app.db.session import get_db

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
