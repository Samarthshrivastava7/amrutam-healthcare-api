from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Doctor(Base):
    __tablename__ = "doctors"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        unique=True,
        index=True,
        nullable=True,
    )
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    specialization: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    qualifications: Mapped[str] = mapped_column(String(255), nullable=False)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
