from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.appointment import AppointmentStatus


class AppointmentCreate(BaseModel):
    doctor_id: int = Field(gt=0)
    scheduled_at: datetime

    @field_validator("scheduled_at")
    @classmethod
    def validate_scheduled_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(
                "scheduled_at must include a timezone, e.g. +05:30"
            )

        if value <= datetime.now(timezone.utc):
            raise ValueError("Appointment time must be in the future")

        return value.astimezone(timezone.utc)


class AppointmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    doctor_id: int
    scheduled_at: datetime
    status: AppointmentStatus
    created_at: datetime | None = None
