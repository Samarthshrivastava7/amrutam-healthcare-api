from pydantic import BaseModel, ConfigDict, Field


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
