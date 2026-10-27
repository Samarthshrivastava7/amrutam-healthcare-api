import os

# These are isolated, non-production settings required while importing the app.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://test:test@127.0.0.1:5432/amrutam_test",
)
os.environ.setdefault(
    "JWT_SECRET_KEY",
    "test-only-secret-not-for-production-0123456789",
)
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import Base, get_db
from main import app


@pytest.fixture
def client():
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
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_root_health_message(client):
    response = client.get("/")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["message"] == "Amrutam Healthcare API is running"


def test_liveness_check_does_not_require_database(client):
    response = client.get("/health/live")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["service"] == "amrutam-backend"
    assert isinstance(body["timestamp"], str)
    assert "database" not in body


def test_readiness_endpoint_confirms_database_connection(client):
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["service"] == "amrutam-backend"
    assert body["database"] == "connected"
    assert isinstance(body["timestamp"], str)


def test_readiness_endpoint_returns_503_when_database_is_unavailable(client):
    def unavailable_db():
        class UnavailableDatabase:
            def execute(self, _statement):
                raise SQLAlchemyError("synthetic database outage")

        yield UnavailableDatabase()

    app.dependency_overrides[get_db] = unavailable_db
    response = client.get("/health/ready")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "unavailable"
    assert body["database"] == "unavailable"
    assert "synthetic database outage" not in response.text
