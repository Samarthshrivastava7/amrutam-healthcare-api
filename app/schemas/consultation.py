from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ConsultationStart(BaseModel):
    appointment_id: int = Field(gt=0)


class ConsultationUpdate(BaseModel):
    notes: str = Field(min_length=1, max_length=10000)

    @field_validator("notes", mode="before")
    @classmethod
    def normalize_notes(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class ConsultationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    appointment_id: int
    notes: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
