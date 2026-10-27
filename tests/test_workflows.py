import os
from datetime import datetime, timedelta, timezone

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://test:test@127.0.0.1:5432/amrutam_test",
)
os.environ.setdefault(
    "JWT_SECRET_KEY",
    "workflow-test-secret-never-use-in-production-123456",
)
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.session import Base, get_db
from app.models.doctor import Doctor
from app.models.user import User, UserRole
from main import app

PATIENT_PASSWORD = "StrongPatientPassword123!"
DOCTOR_PASSWORD = "StrongDoctorPassword123!"


@pytest.fixture
def workflow_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as client:
            yield client, testing_session_local
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def register_and_login_patient(client, email="patient@example.com"):
    registered = client.post(
        "/auth/register",
        json={
            "full_name": "Test Patient",
            "email": email,
            "password": PATIENT_PASSWORD,
        },
    )
    assert registered.status_code == 201, registered.text
    logged_in = client.post(
        "/auth/login",
        json={"email": email, "password": PATIENT_PASSWORD},
    )
    assert logged_in.status_code == 200, logged_in.text
    return {"Authorization": f"Bearer {logged_in.json()['access_token']}"}


def create_doctor_account(session_factory, email="doctor@example.com"):
    with session_factory() as db:
        user = User(
            full_name="Dr Test Example",
            email=email,
            password_hash=hash_password(DOCTOR_PASSWORD),
            role=UserRole.DOCTOR,
            is_active=True,
        )
        db.add(user)
        db.flush()

        doctor = Doctor(
            user_id=user.id,
            full_name="Dr Test Example",
            specialization="General Medicine",
            qualifications="MBBS",
            bio="Synthetic test profile",
            is_active=True,
        )
        db.add(doctor)
        db.commit()
        doctor_id = doctor.id

    return doctor_id


def doctor_headers(client, email="doctor@example.com"):
    response = client.post(
        "/auth/login",
        json={"email": email, "password": DOCTOR_PASSWORD},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def book_appointment(client, headers, doctor_id, when=None, idempotency_key=None):
    if when is None:
        when = (datetime.now(timezone.utc) + timedelta(days=7)).replace(
            microsecond=0
        ).isoformat()

    extra_headers = dict(headers)
    if idempotency_key:
        extra_headers["Idempotency-Key"] = idempotency_key

    response = client.post(
        "/appointments/",
        headers=extra_headers,
        json={"doctor_id": doctor_id, "scheduled_at": when},
    )
    return response, when


def test_patient_doctor_consultation_and_prescription_workflow(workflow_client):
    client, session_factory = workflow_client
    patient_headers = register_and_login_patient(client)
    doctor_id = create_doctor_account(session_factory)
    doctor_auth = doctor_headers(client)

    booked, _ = book_appointment(client, patient_headers, doctor_id)
    assert booked.status_code == 201, booked.text
    appointment_id = booked.json()["id"]

    # Both roles can see the appointment only in their own role-scoped view.
    patient_list = client.get("/appointments/me", headers=patient_headers)
    doctor_list = client.get("/appointments/me", headers=doctor_auth)
    assert patient_list.status_code == 200
    assert [item["id"] for item in patient_list.json()] == [appointment_id]
    assert doctor_list.status_code == 200
    assert [item["id"] for item in doctor_list.json()] == [appointment_id]

    doctor_detail = client.get(
        f"/appointments/{appointment_id}", headers=doctor_auth
    )
    assert doctor_detail.status_code == 200

    patient_cannot_start = client.post(
        "/consultations/",
        headers=patient_headers,
        json={"appointment_id": appointment_id},
    )
    assert patient_cannot_start.status_code == 403

    started = client.post(
        "/consultations/",
        headers=doctor_auth,
        json={"appointment_id": appointment_id},
    )
    assert started.status_code == 201, started.text
    consultation_id = started.json()["id"]

    notes = client.patch(
        f"/consultations/{consultation_id}",
        headers=doctor_auth,
        json={"notes": "  Synthetic clinical note for testing  "},
    )
    assert notes.status_code == 200, notes.text
    assert notes.json()["notes"] == "Synthetic clinical note for testing"

    patient_consultations = client.get(
        "/consultations/me", headers=patient_headers
    )
    assert patient_consultations.status_code == 200
    assert [item["id"] for item in patient_consultations.json()] == [
        consultation_id
    ]

    completed = client.post(
        f"/consultations/{consultation_id}/complete",
        headers=doctor_auth,
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["completed_at"] is not None

    finalized_notes = client.patch(
        f"/consultations/{consultation_id}",
        headers=doctor_auth,
        json={"notes": "Changed after finalization"},
    )
    assert finalized_notes.status_code == 409

    created_prescription = client.post(
        "/prescriptions/",
        headers=doctor_auth,
        json={
            "consultation_id": consultation_id,
            "medication_details": "Synthetic test-only prescription data",
            "instructions": "Not for clinical use",
        },
    )
    assert created_prescription.status_code == 201, created_prescription.text
    prescription_id = created_prescription.json()["id"]

    patient_prescriptions = client.get(
        "/prescriptions/me", headers=patient_headers
    )
    assert patient_prescriptions.status_code == 200
    assert [item["id"] for item in patient_prescriptions.json()] == [
        prescription_id
    ]


def test_patient_cannot_read_another_patients_appointment(workflow_client):
    client, session_factory = workflow_client
    first_patient = register_and_login_patient(client, "first@example.com")
    second_patient = register_and_login_patient(client, "second@example.com")
    doctor_id = create_doctor_account(session_factory)

    booked, _ = book_appointment(client, first_patient, doctor_id)
    assert booked.status_code == 201, booked.text
    appointment_id = booked.json()["id"]

    response = client.get(
        f"/appointments/{appointment_id}",
        headers=second_patient,
    )
    assert response.status_code == 404

    second_patient_list = client.get("/appointments/me", headers=second_patient)
    assert second_patient_list.status_code == 200
    assert all(item["id"] != appointment_id for item in second_patient_list.json())


def test_cancelled_appointment_cannot_start_consultation(workflow_client):
    client, session_factory = workflow_client
    patient_auth = register_and_login_patient(client)
    doctor_id = create_doctor_account(session_factory)
    doctor_auth = doctor_headers(client)

    booked, _ = book_appointment(client, patient_auth, doctor_id)
    assert booked.status_code == 201, booked.text
    appointment_id = booked.json()["id"]

    cancelled = client.post(
        f"/appointments/{appointment_id}/cancel",
        headers=patient_auth,
    )
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["status"].lower() == "cancelled"

    started = client.post(
        "/consultations/",
        headers=doctor_auth,
        json={"appointment_id": appointment_id},
    )
    assert started.status_code == 409


def test_booking_idempotency_and_doctor_time_conflict(workflow_client):
    client, session_factory = workflow_client
    patient_auth = register_and_login_patient(client)
    another_patient = register_and_login_patient(client, "another@example.com")
    doctor_id = create_doctor_account(session_factory)

    first, when = book_appointment(
        client,
        patient_auth,
        doctor_id,
        idempotency_key="test-booking-001",
    )
    assert first.status_code == 201, first.text

    replay, _ = book_appointment(
        client,
        patient_auth,
        doctor_id,
        when=when,
        idempotency_key="test-booking-001",
    )
    assert replay.status_code == 201, replay.text
    assert replay.json()["id"] == first.json()["id"]

    conflict, _ = book_appointment(
        client,
        another_patient,
        doctor_id,
        when=when,
    )
    assert conflict.status_code == 409
