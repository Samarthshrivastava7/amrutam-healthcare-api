from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.routes.auth import get_current_user
from app.db.session import get_db
from app.models.appointment import Appointment, AppointmentStatus
from app.models.consultation import Consultation
from app.models.doctor import Doctor
from app.models.user import User, UserRole
from app.schemas.consultation import ConsultationResponse, ConsultationStart

router = APIRouter(prefix="/consultations", tags=["Consultations"])


def require_doctor(user: User, db: Session) -> Doctor:
    if user.role != UserRole.DOCTOR:
        raise HTTPException(status_code=403, detail="Doctor access required")

    doctor = db.scalar(
        select(Doctor).where(
            Doctor.user_id == user.id,
            Doctor.is_active.is_(True),
        )
    )
    if doctor is None:
        raise HTTPException(status_code=403, detail="No active doctor profile linked")
    return doctor


@router.post("/", response_model=ConsultationResponse, status_code=201)
def start_consultation(
    data: ConsultationStart,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doctor = require_doctor(current_user, db)

    appointment = db.scalar(
        select(Appointment)
        .where(Appointment.id == data.appointment_id)
        .with_for_update()
    )

    if appointment is None:
        raise HTTPException(status_code=404, detail="Appointment not found")

    if appointment.doctor_id != doctor.id:
        raise HTTPException(status_code=403, detail="This appointment is not assigned to you")

    if appointment.status != AppointmentStatus.BOOKED:
        raise HTTPException(status_code=409, detail="Appointment is not booked")

    existing = db.scalar(
        select(Consultation).where(
            Consultation.appointment_id == appointment.id
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Consultation already exists")

    consultation = Consultation(
        appointment_id=appointment.id,
        started_at=datetime.now(timezone.utc),
    )
    db.add(consultation)

    try:
        db.commit()
        db.refresh(consultation)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Consultation already exists")

    return consultation


@router.get("/me", response_model=list[ConsultationResponse])
def list_my_consultations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role == UserRole.DOCTOR:
        doctor = require_doctor(current_user, db)
        statement = (
            select(Consultation)
            .join(Appointment, Consultation.appointment_id == Appointment.id)
            .where(Appointment.doctor_id == doctor.id)
            .order_by(Consultation.id.desc())
        )
    elif current_user.role == UserRole.PATIENT:
        statement = (
            select(Consultation)
            .join(Appointment, Consultation.appointment_id == Appointment.id)
            .where(Appointment.patient_id == current_user.id)
            .order_by(Consultation.id.desc())
        )
    else:
        raise HTTPException(status_code=403, detail="Patient or doctor access required")

    return list(db.scalars(statement).all())


@router.post("/{consultation_id}/complete", response_model=ConsultationResponse)
def complete_consultation(
    consultation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doctor = require_doctor(current_user, db)

    consultation = db.scalar(
        select(Consultation)
        .join(Appointment, Consultation.appointment_id == Appointment.id)
        .where(
            Consultation.id == consultation_id,
            Appointment.doctor_id == doctor.id,
        )
        .with_for_update()
    )

    if consultation is None:
        raise HTTPException(status_code=404, detail="Consultation not found")

    if consultation.completed_at is not None:
        raise HTTPException(status_code=409, detail="Consultation already completed")

    appointment = db.get(Appointment, consultation.appointment_id)
    if appointment is None or appointment.status != AppointmentStatus.BOOKED:
        raise HTTPException(status_code=409, detail="Appointment is not booked")

    consultation.completed_at = datetime.now(timezone.utc)
    appointment.status = AppointmentStatus.COMPLETED

    db.commit()
    db.refresh(consultation)
    return consultation
