"""PostgreSQL-only integration tests for database locking and concurrent writes.

These tests are skipped locally unless POSTGRES_TEST_URL points at a disposable
PostgreSQL database. CI provisions an ephemeral PostgreSQL service for them.
"""
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.security import hash_password
from app.db.session import Base, get_db
from app.models.doctor import Doctor
from app.models.user import User, UserRole
from main import app

POSTGRES_TEST_URL = os.getenv("POSTGRES_TEST_URL")
pytestmark = pytest.mark.skipif(
    not POSTGRES_TEST_URL,
    reason="POSTGRES_TEST_URL is not configured; PostgreSQL concurrency test skipped",
)
PATIENT_PASSWORD = "StrongPatientPassword123!"
DOCTOR_PASSWORD = "StrongDoctorPassword123!"


@pytest.fixture
def postgres_client():
    engine = create_engine(POSTGRES_TEST_URL, pool_size=10, max_overflow=10)
    factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            yield client, factory
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def _patient_headers(client):
    email = "pg-concurrency-patient@example.com"
    registered = client.post(
        "/auth/register",
        json={"full_name": "Synthetic Patient", "email": email, "password": PATIENT_PASSWORD},
    )
    assert registered.status_code == 201, registered.text
    logged = client.post("/auth/login", json={"email": email, "password": PATIENT_PASSWORD})
    assert logged.status_code == 200, logged.text
    return {"Authorization": f"Bearer {logged.json()['access_token']}"}


def _doctor(client, factory):
    with factory() as db:
        user = User(
            full_name="Synthetic Doctor",
            email="pg-concurrency-doctor@example.com",
            password_hash=hash_password(DOCTOR_PASSWORD),
            role=UserRole.DOCTOR,
            is_active=True,
        )
        db.add(user)
        db.flush()
        doctor = Doctor(
            user_id=user.id,
            full_name="Synthetic Doctor",
            specialization="General Medicine",
            qualifications="MBBS",
            bio="Synthetic PostgreSQL integration-test profile",
            is_active=True,
        )
        db.add(doctor)
        db.commit()
        return doctor.id


def test_postgres_concurrent_booking_allows_only_one_booking(postgres_client):
    client, factory = postgres_client
    patient_headers = _patient_headers(client)
    doctor_id = _doctor(client, factory)
    scheduled_at = (datetime.now(timezone.utc) + timedelta(days=15)).replace(
        microsecond=0
    ).isoformat()

    def attempt():
        return client.post(
            "/appointments/",
            headers=patient_headers,
            json={"doctor_id": doctor_id, "scheduled_at": scheduled_at},
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: attempt(), range(2)))

    assert sorted(response.status_code for response in responses) == [201, 409]
    with factory() as db:
        from app.models.appointment import Appointment, AppointmentStatus
        count = (
            db.query(Appointment)
            .filter(
                Appointment.doctor_id == doctor_id,
                Appointment.status == AppointmentStatus.BOOKED,
            )
            .count()
        )
        assert count == 1


def test_postgres_concurrent_overlapping_availability_is_rejected(postgres_client):
    client, factory = postgres_client
    _patient_headers(client)
    doctor_id = _doctor(client, factory)
    doctor_login = client.post(
        "/auth/login",
        json={"email": "pg-concurrency-doctor@example.com", "password": DOCTOR_PASSWORD},
    )
    assert doctor_login.status_code == 200, doctor_login.text
    headers = {"Authorization": f"Bearer {doctor_login.json()['access_token']}"}
    starts_at = (datetime.now(timezone.utc) + timedelta(days=20)).replace(
        microsecond=0
    )

    def attempt(offset_minutes):
        start = starts_at + timedelta(minutes=offset_minutes)
        return client.post(
            "/doctors/me/availability",
            headers=headers,
            json={
                "starts_at": start.isoformat(),
                "ends_at": (start + timedelta(minutes=30)).isoformat(),
            },
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(attempt, [0, 15]))

    assert sorted(response.status_code for response in responses) == [201, 409]
