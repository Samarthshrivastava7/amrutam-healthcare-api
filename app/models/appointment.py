import enum
from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.db.session import Base


class AppointmentStatus(str, enum.Enum):
    BOOKED = "booked"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"), nullable=False, index=True)
    scheduled_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    status: Mapped[AppointmentStatus] = mapped_column(
        Enum(AppointmentStatus), default=AppointmentStatus.BOOKED, nullable=False
    )
    idempotency_key: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
