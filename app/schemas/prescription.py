from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PrescriptionCreate(BaseModel):
    consultation_id: int = Field(gt=0)
    medication_details: str = Field(min_length=1, max_length=10000)
    instructions: str | None = Field(default=None, max_length=5000)

    @field_validator("medication_details", mode="before")
    @classmethod
    def normalize_medication_details(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("instructions", mode="before")
    @classmethod
    def normalize_instructions(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value


class PrescriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    consultation_id: int
    medication_details: str
    instructions: str | None = None
    created_at: datetime | None = None
