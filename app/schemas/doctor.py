from pydantic import BaseModel, ConfigDict, Field, field_validator


class DoctorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    specialization: str
    qualifications: str
    bio: str | None = None
    is_active: bool


class DoctorCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    specialization: str = Field(min_length=2, max_length=120)
    qualifications: str = Field(min_length=2, max_length=255)
    bio: str | None = Field(default=None, max_length=5000)

    @field_validator("full_name", "specialization", "qualifications", mode="before")
    @classmethod
    def normalize_required_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("bio", mode="before")
    @classmethod
    def normalize_bio(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value
