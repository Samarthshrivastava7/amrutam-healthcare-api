from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ConsultationStart(BaseModel):
    appointment_id: int = Field(gt=0)


class ConsultationUpdate(BaseModel):
    notes: str = Field(min_length=1, max_length=10000)


class ConsultationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    appointment_id: int
    notes: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
