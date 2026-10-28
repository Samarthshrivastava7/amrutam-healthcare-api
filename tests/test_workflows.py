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
from app.models.audit_log import AuditLog
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


def test_same_patient_cannot_book_two_doctors_at_same_time(workflow_client):
    client, session_factory = workflow_client
    patient_auth = register_and_login_patient(client)
    first_doctor_id = create_doctor_account(session_factory, "doctor1@example.com")
    second_doctor_id = create_doctor_account(session_factory, "doctor2@example.com")
    first, when = book_appointment(client, patient_auth, first_doctor_id)
    assert first.status_code == 201, first.text

    conflict, _ = book_appointment(
        client, patient_auth, second_doctor_id, when=when
    )
    assert conflict.status_code == 409


def test_idempotency_key_cannot_be_reused_for_different_booking(workflow_client):
    client, session_factory = workflow_client
    patient_auth = register_and_login_patient(client)
    doctor_id = create_doctor_account(session_factory)
    first, when = book_appointment(
        client, patient_auth, doctor_id, idempotency_key="reuse-key-001"
    )
    assert first.status_code == 201, first.text

    different_time = (
        datetime.fromisoformat(when) + timedelta(hours=1)
    ).isoformat()
    conflict, _ = book_appointment(
        client,
        patient_auth,
        doctor_id,
        when=different_time,
        idempotency_key="reuse-key-001",
    )
    assert conflict.status_code == 409


def test_cancelled_doctor_slot_can_be_booked_again(workflow_client):
    client, session_factory = workflow_client
    patient_auth = register_and_login_patient(client)
    another_patient = register_and_login_patient(client, "replacement@example.com")
    doctor_id = create_doctor_account(session_factory)
    first, when = book_appointment(client, patient_auth, doctor_id)
    assert first.status_code == 201, first.text

    cancelled = client.post(
        f"/appointments/{first.json()['id']}/cancel", headers=patient_auth
    )
    assert cancelled.status_code == 200, cancelled.text

    replacement, _ = book_appointment(
        client, another_patient, doctor_id, when=when
    )
    assert replacement.status_code == 201, replacement.text


def test_doctor_publishes_availability_and_booking_uses_published_slot(workflow_client):
    client, session_factory = workflow_client
    patient_auth = register_and_login_patient(client)
    doctor_id = create_doctor_account(session_factory)
    doctor_auth = doctor_headers(client)
    starts_at = (datetime.now(timezone.utc) + timedelta(days=8)).replace(
        microsecond=0
    )
    ends_at = starts_at + timedelta(minutes=30)

    published = client.post(
        "/doctors/me/availability",
        headers=doctor_auth,
        json={"starts_at": starts_at.isoformat(), "ends_at": ends_at.isoformat()},
    )
    assert published.status_code == 201, published.text
    slot = published.json()
    assert slot["doctor_id"] == doctor_id

    listed = client.get(f"/doctors/{doctor_id}/availability")
    assert listed.status_code == 200, listed.text
    assert any(item["id"] == slot["id"] for item in listed.json())

    outside_slot = starts_at + timedelta(hours=1)
    rejected, _ = book_appointment(
        client, patient_auth, doctor_id, when=outside_slot.isoformat()
    )
    assert rejected.status_code == 409

    accepted, _ = book_appointment(
        client, patient_auth, doctor_id, when=starts_at.isoformat()
    )
    assert accepted.status_code == 201, accepted.text


def test_doctor_cannot_publish_overlapping_availability(workflow_client):
    client, session_factory = workflow_client
    create_doctor_account(session_factory)
    doctor_auth = doctor_headers(client)
    starts_at = (datetime.now(timezone.utc) + timedelta(days=9)).replace(
        microsecond=0
    )
    first = client.post(
        "/doctors/me/availability",
        headers=doctor_auth,
        json={
            "starts_at": starts_at.isoformat(),
            "ends_at": (starts_at + timedelta(minutes=30)).isoformat(),
        },
    )
    assert first.status_code == 201, first.text

    overlap = client.post(
        "/doctors/me/availability",
        headers=doctor_auth,
        json={
            "starts_at": (starts_at + timedelta(minutes=15)).isoformat(),
            "ends_at": (starts_at + timedelta(minutes=45)).isoformat(),
        },
    )
    assert overlap.status_code == 409


def test_patient_cannot_publish_doctor_availability(workflow_client):
    client, _ = workflow_client
    patient_auth = register_and_login_patient(client)
    starts_at = (datetime.now(timezone.utc) + timedelta(days=10)).replace(
        microsecond=0
    )
    response = client.post(
        "/doctors/me/availability",
        headers=patient_auth,
        json={
            "starts_at": starts_at.isoformat(),
            "ends_at": (starts_at + timedelta(minutes=30)).isoformat(),
        },
    )
    assert response.status_code == 403



def test_booking_writes_metadata_only_audit_log(workflow_client):
    client, session_factory = workflow_client
    patient_auth = register_and_login_patient(client)
    doctor_id = create_doctor_account(session_factory)
    response, _ = book_appointment(client, patient_auth, doctor_id)
    assert response.status_code == 201, response.text
    appointment_id = response.json()["id"]
    with session_factory() as db:
        logs = (
            db.query(AuditLog)
            .filter_by(resource_id=str(appointment_id), action="appointment.booked")
            .all()
        )
        assert len(logs) == 1
        assert logs[0].action == "appointment.booked"
        assert logs[0].resource_type == "appointment"
        assert logs[0].actor_user_id is not None
        assert not hasattr(logs[0], "clinical_notes")


def test_admin_analytics_requires_admin_and_returns_aggregates(workflow_client):
    client, session_factory = workflow_client
    patient_auth = register_and_login_patient(client)
    denied = client.get("/admin/analytics/overview", headers=patient_auth)
    assert denied.status_code == 403

    with session_factory() as db:
        admin = User(
            full_name="Test Admin",
            email="admin@example.com",
            password_hash=hash_password("StrongAdminPassword123!"),
            role=UserRole.ADMIN,
            is_active=True,
        )
        db.add(admin)
        db.commit()
    login = client.post(
        "/auth/login",
        json={"email": "admin@example.com", "password": "StrongAdminPassword123!"},
    )
    assert login.status_code == 200, login.text
    admin_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    response = client.get("/admin/analytics/overview", headers=admin_headers)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert "users_by_role" in payload
    assert "appointments_by_status" in payload
    assert "consultations_total" in payload
    assert "generated_at" in payload

def test_registration_and_successful_login_write_metadata_audit_logs(workflow_client):
    client, session_factory = workflow_client
    registered = client.post(
        "/auth/register",
        json={
            "full_name": "Audit Test Patient",
            "email": "audit-patient@example.com",
            "password": PATIENT_PASSWORD,
        },
    )
    assert registered.status_code == 201, registered.text

    logged_in = client.post(
        "/auth/login",
        json={
            "email": "audit-patient@example.com",
            "password": PATIENT_PASSWORD,
        },
    )
    assert logged_in.status_code == 200, logged_in.text

    with session_factory() as db:
        logs = (
            db.query(AuditLog)
            .filter(AuditLog.resource_type == "user")
            .order_by(AuditLog.id.asc())
            .all()
        )
        assert [log.action for log in logs] == [
            "auth.registered",
            "auth.login_succeeded",
        ]
        assert all(log.actor_user_id == registered.json()["id"] for log in logs)
        assert all(not hasattr(log, "password") for log in logs)

