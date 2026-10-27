import os

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://test:test@127.0.0.1:5432/amrutam_test",
)
os.environ["JWT_SECRET_KEY"] = "isolated-test-secret-not-for-production"
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from app.db.session import Base, get_db
from app.models.user import User
from app.models.doctor import Doctor
from app.models.appointment import Appointment
from app.models.consultation import Consultation
from app.models.prescription import Prescription


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def register_patient(client, email="patient@example.com"):
    return client.post(
        "/auth/register",
        json={
            "full_name": "Test Patient",
            "email": email,
            "password": "StrongTestPass123!",
        },
    )


def login_patient(client, email="patient@example.com"):
    return client.post(
        "/auth/login",
        json={
            "email": email,
            "password": "StrongTestPass123!",
        },
    )


def test_register_patient_success(client):
    response = register_patient(client)
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "patient@example.com"
    assert body["role"].lower() == "patient"
    assert "password_hash" not in body


def test_duplicate_email_returns_conflict(client):
    first = register_patient(client)
    second = register_patient(client)
    assert first.status_code == 201
    assert second.status_code == 409


def test_login_returns_access_token(client):
    assert register_patient(client).status_code == 201
    response = login_patient(client)
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]


def test_wrong_password_returns_401(client):
    assert register_patient(client).status_code == 201
    response = client.post(
        "/auth/login",
        json={
            "email": "patient@example.com",
            "password": "WrongPassword123!",
        },
    )
    assert response.status_code == 401


def test_me_requires_authentication(client):
    response = client.get("/auth/me")
    assert response.status_code in (401, 403)


def test_patient_cannot_create_doctor(client):
    assert register_patient(client).status_code == 201
    login_response = login_patient(client)
    assert login_response.status_code == 200

    token = login_response.json()["access_token"]
    response = client.post(
        "/doctors/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "full_name": "Test Doctor",
            "specialization": "Cardiology",
            "qualifications": "MBBS, MD",
            "bio": "Test profile",
        },
    )
    assert response.status_code == 403
