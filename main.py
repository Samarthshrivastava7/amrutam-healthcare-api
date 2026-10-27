from datetime import datetime, timezone

from fastapi import FastAPI

from app.api.routes.auth import router as auth_router
from app.api.routes.doctors import router as doctors_router
from app.api.routes.appointments import router as appointments_router
from app.api.routes.consultations import router as consultations_router
from app.api.routes.prescriptions import router as prescriptions_router

app = FastAPI(
    title="Amrutam Healthcare API",
    description="Backend API for doctor appointments and healthcare consultations",
    version="1.0.0",
)

app.include_router(auth_router)
app.include_router(doctors_router)
app.include_router(appointments_router)
app.include_router(consultations_router)
app.include_router(prescriptions_router)


@app.get("/", tags=["Health"])
def home():
    return {
        "message": "Amrutam Healthcare API is running",
        "status": "success",
    }


@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": "amrutam-backend",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
