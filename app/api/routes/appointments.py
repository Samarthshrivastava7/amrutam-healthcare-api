from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.routes.auth import get_current_user
from app.db.session import get_db
from app.models.appointment import Appointment, AppointmentStatus
from app.models.doctor import Doctor
from app.models.user import User, UserRole
from app.schemas.appointment import AppointmentCreate, AppointmentResponse

router = APIRouter(prefix="/appointments", tags=["Appointments"])


def require_patient(user: User) -> None:
    if user.role != UserRole.PATIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Patient account required",
        )


def require_doctor(user: User, db: Session) -> Doctor:
    if user.role != UserRole.DOCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Doctor account required",
        )

    doctor = db.scalar(
        select(Doctor).where(
            Doctor.user_id == user.id,
            Doctor.is_active.is_(True),
        )
    )
    if doctor is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No active doctor profile linked",
        )
    return doctor


@router.post(
    "/",
    response_model=AppointmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def book_appointment(
    data: AppointmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
        min_length=1,
        max_length=128,
    ),
):
    require_patient(current_user)

    scheduled_at = data.scheduled_at.astimezone(timezone.utc)

    # A retry using the same key must not create a second appointment.
    if idempotency_key:
        previous = db.scalar(
            select(Appointment).where(
                Appointment.idempotency_key == idempotency_key
            )
        )
        if previous:
            if (
                previous.patient_id == current_user.id
                and previous.doctor_id == data.doctor_id
                and previous.scheduled_at == scheduled_at
            ):
                return previous

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Idempotency key has already been used",
            )

    # Serialize bookings for this doctor on databases that support row locks.
    doctor = db.scalar(
        select(Doctor)
        .where(
            Doctor.id == data.doctor_id,
            Doctor.is_active.is_(True),
        )
        .with_for_update()
    )

    if doctor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active doctor not found",
        )

    doctor_conflict = db.scalar(
        select(Appointment.id).where(
            Appointment.doctor_id == data.doctor_id,
            Appointment.scheduled_at == scheduled_at,
            Appointment.status == AppointmentStatus.BOOKED,
        )
    )
    if doctor_conflict is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Doctor already has an appointment at this time",
        )

    patient_conflict = db.scalar(
        select(Appointment.id).where(
            Appointment.patient_id == current_user.id,
            Appointment.scheduled_at == scheduled_at,
            Appointment.status == AppointmentStatus.BOOKED,
        )
    )
    if patient_conflict is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have an appointment at this time",
        )

    appointment = Appointment(
        patient_id=current_user.id,
        doctor_id=data.doctor_id,
        scheduled_at=scheduled_at,
        status=AppointmentStatus.BOOKED,
        idempotency_key=idempotency_key,
    )

    db.add(appointment)
    try:
        db.commit()
        db.refresh(appointment)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Booking conflict or duplicate idempotency key",
        )

    return appointment


@router.get("/me", response_model=list[AppointmentResponse])
def list_my_appointments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List only appointments belonging to the authenticated patient or doctor."""
    if current_user.role == UserRole.PATIENT:
        statement = select(Appointment).where(
            Appointment.patient_id == current_user.id
        )
    elif current_user.role == UserRole.DOCTOR:
        doctor = require_doctor(current_user, db)
        statement = select(Appointment).where(Appointment.doctor_id == doctor.id)
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Patient or doctor account required",
        )

    statement = statement.order_by(Appointment.scheduled_at.desc())
    return list(db.scalars(statement).all())


@router.get("/{appointment_id}", response_model=AppointmentResponse)
def get_my_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return an appointment only when the caller is its patient or assigned doctor."""
    if current_user.role == UserRole.PATIENT:
        ownership_filter = Appointment.patient_id == current_user.id
    elif current_user.role == UserRole.DOCTOR:
        doctor = require_doctor(current_user, db)
        ownership_filter = Appointment.doctor_id == doctor.id
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Patient or doctor account required",
        )

    appointment = db.scalar(
        select(Appointment).where(
            Appointment.id == appointment_id,
            ownership_filter,
        )
    )
    if appointment is None:
        # Deliberately do not reveal whether another user's appointment exists.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )

    return appointment


@router.post(
    "/{appointment_id}/cancel",
    response_model=AppointmentResponse,
)
def cancel_my_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_patient(current_user)

    appointment = db.scalar(
        select(Appointment)
        .where(
            Appointment.id == appointment_id,
            Appointment.patient_id == current_user.id,
        )
        .with_for_update()
    )

    if appointment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )

    if appointment.status != AppointmentStatus.BOOKED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only booked appointments can be cancelled",
        )

    appointment.status = AppointmentStatus.CANCELLED
    db.commit()
    db.refresh(appointment)

    return appointment
