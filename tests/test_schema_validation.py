import pytest
from pydantic import ValidationError

from app.schemas.doctor import DoctorCreate
from app.schemas.prescription import PrescriptionCreate
from app.schemas.user import UserRegister


def test_registration_name_is_trimmed():
    user = UserRegister(
        full_name="  Samarth Shrivastava  ",
        email="samarth@example.com",
        password="StrongTestPassword123!",
    )
    assert user.full_name == "Samarth Shrivastava"


@pytest.mark.parametrize("name", ["", " ", "   "])
def test_registration_rejects_blank_name(name):
    with pytest.raises(ValidationError):
        UserRegister(
            full_name=name,
            email="samarth@example.com",
            password="StrongTestPassword123!",
        )


def test_doctor_required_fields_are_trimmed():
    doctor = DoctorCreate(
        full_name="  Dr Example ",
        specialization=" General Medicine ",
        qualifications=" MBBS ",
        bio="   ",
    )
    assert doctor.full_name == "Dr Example"
    assert doctor.specialization == "General Medicine"
    assert doctor.qualifications == "MBBS"
    assert doctor.bio is None


@pytest.mark.parametrize(
    "payload",
    [
        {"full_name": "Dr Example", "specialization": "  ", "qualifications": "MBBS"},
        {"full_name": "  ", "specialization": "Cardiology", "qualifications": "MBBS"},
        {"full_name": "Dr Example", "specialization": "Cardiology", "qualifications": "  "},
    ],
)
def test_doctor_rejects_blank_required_fields(payload):
    with pytest.raises(ValidationError):
        DoctorCreate(**payload)


def test_prescription_text_is_trimmed_and_blank_instructions_become_none():
    prescription = PrescriptionCreate(
        consultation_id=1,
        medication_details="  Test-only medication details  ",
        instructions="   ",
    )
    assert prescription.medication_details == "Test-only medication details"
    assert prescription.instructions is None


@pytest.mark.parametrize("details", ["", " ", "   "])
def test_prescription_rejects_blank_medication_details(details):
    with pytest.raises(ValidationError):
        PrescriptionCreate(
            consultation_id=1,
            medication_details=details,
        )
