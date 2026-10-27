import os

# The health endpoint does not access the database, but importing the app
# requires these settings to be present. Existing environment variables win.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://test:test@127.0.0.1:5432/amrutam_test",
)
os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret-not-for-production")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")

from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_root_health_message():
    response = client.get("/")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["message"] == "Amrutam Healthcare API is running"


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["service"] == "amrutam-backend"
    assert isinstance(body["timestamp"], str)
