from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.db.session import Base


class Consultation(Base):
    __tablename__ = "consultations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    appointment_id: Mapped[int] = mapped_column(ForeignKey("appointments.id"), unique=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
