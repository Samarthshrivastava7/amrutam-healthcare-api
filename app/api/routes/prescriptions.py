from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routes.auth import get_current_user
from app.db.session import get_db
from app.models.appointment import Appointment
from app.models.audit_log import AuditLog
from app.models.consultation import Consultation
from app.models.doctor import Doctor
from app.models.prescription import Prescription
from app.models.user import User, UserRole
from app.schemas.prescription import PrescriptionCreate, PrescriptionResponse

router = APIRouter(prefix="/prescriptions", tags=["Prescriptions"])


@router.post("/", response_model=PrescriptionResponse, status_code=201)
def create_prescription(
    data: PrescriptionCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != UserRole.DOCTOR:
        raise HTTPException(status_code=403, detail="Doctor access required")

    doctor = db.scalar(
        select(Doctor).where(
            Doctor.user_id == current_user.id,
            Doctor.is_active.is_(True),
        )
    )
    if doctor is None:
        raise HTTPException(status_code=403, detail="No active doctor profile linked")

    consultation = db.scalar(
        select(Consultation)
        .join(Appointment, Consultation.appointment_id == Appointment.id)
        .where(
            Consultation.id == data.consultation_id,
            Appointment.doctor_id == doctor.id,
        )
    )
    if consultation is None:
        raise HTTPException(status_code=404, detail="Consultation not found")

    prescription = Prescription(
        consultation_id=consultation.id,
        medication_details=data.medication_details.strip(),
        instructions=data.instructions.strip() if data.instructions else None,
    )
    db.add(prescription)
    db.flush()
    db.add(AuditLog(
        actor_user_id=current_user.id,
        action="prescription.created",
        resource_type="prescription",
        resource_id=str(prescription.id),
        request_id=getattr(request.state, "request_id", None),
    ))
    db.commit()
    db.refresh(prescription)
    return prescription


@router.get("/me", response_model=list[PrescriptionResponse])
def list_my_prescriptions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role == UserRole.PATIENT:
        statement = (
            select(Prescription)
            .join(
                Consultation,
                Prescription.consultation_id == Consultation.id,
            )
            .join(
                Appointment,
                Consultation.appointment_id == Appointment.id,
            )
            .where(Appointment.patient_id == current_user.id)
            .order_by(Prescription.id.desc())
        )
    elif current_user.role == UserRole.DOCTOR:
        doctor = db.scalar(
            select(Doctor).where(
                Doctor.user_id == current_user.id,
                Doctor.is_active.is_(True),
            )
        )
        if doctor is None:
            raise HTTPException(status_code=403, detail="No active doctor profile linked")

        statement = (
            select(Prescription)
            .join(
                Consultation,
                Prescription.consultation_id == Consultation.id,
            )
            .join(
                Appointment,
                Consultation.appointment_id == Appointment.id,
            )
            .where(Appointment.doctor_id == doctor.id)
            .order_by(Prescription.id.desc())
        )
    else:
        raise HTTPException(status_code=403, detail="Patient or doctor access required")

    return list(db.scalars(statement).all())
