from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.routes.auth import get_current_user
from app.core.permissions import get_current_admin
from app.db.session import get_db
from app.models.availability_slot import AvailabilitySlot
from app.models.doctor import Doctor
from app.models.user import User, UserRole
from app.schemas.availability import AvailabilitySlotCreate, AvailabilitySlotResponse
from app.schemas.doctor import DoctorCreate, DoctorResponse

router = APIRouter(prefix="/doctors", tags=["Doctors"])


def _doctor_for_user(db: Session, user: User) -> Doctor:
    if user.role != UserRole.DOCTOR:
        raise HTTPException(status_code=403, detail="Doctor account required")
    doctor = db.scalar(
        select(Doctor).where(Doctor.user_id == user.id, Doctor.is_active.is_(True)).with_for_update()
    )
    if doctor is None:
        raise HTTPException(status_code=403, detail="No active doctor profile linked")
    return doctor


@router.get("/", response_model=list[DoctorResponse])
def list_doctors(
    specialization: str | None = Query(default=None, min_length=2, max_length=120),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    statement = select(Doctor).where(Doctor.is_active.is_(True))
    if specialization:
        statement = statement.where(
            Doctor.specialization.ilike(f"%{specialization.strip()}%")
        )
    statement = statement.order_by(Doctor.full_name).offset(skip).limit(limit)
    return list(db.scalars(statement).all())


@router.post(
    "/me/availability",
    response_model=AvailabilitySlotResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_my_availability(
    data: AvailabilitySlotCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Publish a future slot for the authenticated doctor's own profile."""
    doctor = _doctor_for_user(db, current_user)
    overlap = db.scalar(
        select(AvailabilitySlot.id).where(
            AvailabilitySlot.doctor_id == doctor.id,
            AvailabilitySlot.starts_at < data.ends_at,
            AvailabilitySlot.ends_at > data.starts_at,
        )
    )
    if overlap is not None:
        raise HTTPException(status_code=409, detail="Availability overlaps an existing slot")
    slot = AvailabilitySlot(
        doctor_id=doctor.id, starts_at=data.starts_at, ends_at=data.ends_at
    )
    db.add(slot)
    try:
        db.commit()
        db.refresh(slot)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Availability conflicts with an existing slot")
    return slot


@router.get(
    "/{doctor_id}/availability",
    response_model=list[AvailabilitySlotResponse],
)
def list_doctor_availability(
    doctor_id: int,
    from_time: datetime | None = Query(default=None),
    to_time: datetime | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List future availability windows for an active doctor."""
    doctor = db.scalar(
        select(Doctor).where(Doctor.id == doctor_id, Doctor.is_active.is_(True))
    )
    if doctor is None:
        raise HTTPException(status_code=404, detail="Doctor not found")
    now = datetime.now(timezone.utc)
    if from_time is not None:
        if from_time.tzinfo is None or from_time.utcoffset() is None:
            raise HTTPException(status_code=422, detail="from_time must include a timezone")
        from_time = from_time.astimezone(timezone.utc)
    if to_time is not None:
        if to_time.tzinfo is None or to_time.utcoffset() is None:
            raise HTTPException(status_code=422, detail="to_time must include a timezone")
        to_time = to_time.astimezone(timezone.utc)
    if from_time and to_time and to_time <= from_time:
        raise HTTPException(status_code=422, detail="to_time must be later than from_time")
    statement = select(AvailabilitySlot).where(
        AvailabilitySlot.doctor_id == doctor_id,
        AvailabilitySlot.ends_at > (from_time or now),
    )
    if to_time:
        statement = statement.where(AvailabilitySlot.starts_at < to_time)
    statement = statement.order_by(AvailabilitySlot.starts_at).offset(skip).limit(limit)
    return list(db.scalars(statement).all())


@router.get("/{doctor_id}", response_model=DoctorResponse)
def get_doctor(doctor_id: int, db: Session = Depends(get_db)):
    doctor = db.scalar(
        select(Doctor).where(Doctor.id == doctor_id, Doctor.is_active.is_(True))
    )
    if doctor is None:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return doctor


@router.post("/", response_model=DoctorResponse, status_code=status.HTTP_201_CREATED)
def create_doctor(
    data: DoctorCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    doctor = Doctor(
        full_name=data.full_name.strip(),
        specialization=data.specialization.strip(),
        qualifications=data.qualifications.strip(),
        bio=data.bio.strip() if data.bio else None,
    )
    db.add(doctor)
    db.commit()
    db.refresh(doctor)
    return doctor
