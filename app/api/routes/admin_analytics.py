from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.permissions import get_current_admin
from app.db.session import get_db
from app.models.appointment import Appointment, AppointmentStatus
from app.models.consultation import Consultation
from app.models.doctor import Doctor
from app.models.user import User, UserRole

router = APIRouter(prefix="/admin/analytics", tags=["Admin Analytics"])


@router.get("/overview")
def analytics_overview(
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    """Return aggregate operational counts; never returns patient-level clinical data."""
    appointment_counts = {
        str(status_value.value): int(count)
        for status_value, count in db.execute(
            select(Appointment.status, func.count(Appointment.id)).group_by(
                Appointment.status
            )
        ).all()
    }
    role_counts = {
        str(role_value.value): int(count)
        for role_value, count in db.execute(
            select(User.role, func.count(User.id)).group_by(User.role)
        ).all()
    }
    return {
        "generated_at": datetime.now(timezone.utc),
        "users_by_role": role_counts,
        "active_doctors": int(
            db.scalar(select(func.count(Doctor.id)).where(Doctor.is_active.is_(True))) or 0
        ),
        "appointments_by_status": appointment_counts,
        "consultations_total": int(
            db.scalar(select(func.count(Consultation.id))) or 0
        ),
    }
