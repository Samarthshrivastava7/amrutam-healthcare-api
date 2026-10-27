from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.db.session import Base


class Prescription(Base):
    __tablename__ = "prescriptions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    consultation_id: Mapped[int] = mapped_column(ForeignKey("consultations.id"), nullable=False, index=True)
    medication_details: Mapped[str] = mapped_column(Text, nullable=False)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
