from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PrescriptionCreate(BaseModel):
    consultation_id: int = Field(gt=0)
    medication_details: str = Field(min_length=1, max_length=10000)
    instructions: str | None = Field(default=None, max_length=5000)


class PrescriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    consultation_id: int
    medication_details: str
    instructions: str | None = None
    created_at: datetime | None = None
