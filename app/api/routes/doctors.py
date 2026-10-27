from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.permissions import get_current_admin
from app.db.session import get_db
from app.models.doctor import Doctor
from app.models.user import User
from app.schemas.doctor import DoctorCreate, DoctorResponse

router = APIRouter(prefix="/doctors", tags=["Doctors"])


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


@router.get("/{doctor_id}", response_model=DoctorResponse)
def get_doctor(doctor_id: int, db: Session = Depends(get_db)):
    doctor = db.scalar(
        select(Doctor).where(
            Doctor.id == doctor_id,
            Doctor.is_active.is_(True),
        )
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
