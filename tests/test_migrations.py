import os
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://test:test@127.0.0.1:5432/amrutam_test",
)
os.environ.setdefault(
    "JWT_SECRET_KEY",
    "migration-test-secret-never-use-in-production-12345",
)
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine

from app.db.session import Base
from app.models import appointment, consultation, doctor, prescription, user  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = ROOT / "alembic" / "versions" / "f151f0d1ce55_baseline_existing_schema.py"
DOCTOR_LINK_PATH = ROOT / "alembic" / "versions" / "7f2dc8f87199_link_doctors_to_user_accounts.py"


def load_migration(path: Path, name: str):
    spec = spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


baseline = load_migration(BASELINE_PATH, "amrutam_baseline_migration")
doctor_link = load_migration(DOCTOR_LINK_PATH, "amrutam_doctor_link_migration")


def run_migration(connection, migration, direction="upgrade"):
    context = MigrationContext.configure(connection)
    with Operations.context(context):
        getattr(migration, direction)()


def test_fresh_database_can_upgrade_to_current_schema():
    engine = create_engine("sqlite://")
    try:
        with engine.begin() as connection:
            run_migration(connection, baseline)
            run_migration(connection, doctor_link)

        inspector = sa.inspect(engine)
        assert {
            "users",
            "doctors",
            "appointments",
            "consultations",
            "prescriptions",
        }.issubset(set(inspector.get_table_names()))

        doctor_columns = {column["name"] for column in inspector.get_columns("doctors")}
        assert "user_id" in doctor_columns
        assert any(
            index.get("column_names") == ["user_id"] and index.get("unique")
            for index in inspector.get_indexes("doctors")
        )
        assert any(
            foreign_key.get("constrained_columns") == ["user_id"]
            and foreign_key.get("referred_table") == "users"
            and foreign_key.get("referred_columns") == ["id"]
            for foreign_key in inspector.get_foreign_keys("doctors")
        )
    finally:
        engine.dispose()


def test_existing_current_schema_does_not_get_duplicate_doctor_link_objects():
    engine = create_engine("sqlite://")
    try:
        Base.metadata.create_all(bind=engine)
        with engine.begin() as connection:
            run_migration(connection, baseline)
            run_migration(connection, doctor_link)

        inspector = sa.inspect(engine)
        columns = [column["name"] for column in inspector.get_columns("doctors")]
        assert columns.count("user_id") == 1
        assert sum(
            1
            for index in inspector.get_indexes("doctors")
            if index.get("column_names") == ["user_id"] and index.get("unique")
        ) == 1
        assert sum(
            1
            for foreign_key in inspector.get_foreign_keys("doctors")
            if foreign_key.get("constrained_columns") == ["user_id"]
            and foreign_key.get("referred_table") == "users"
        ) == 1
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_baseline_stops_on_a_partially_initialized_application_schema():
    engine = create_engine("sqlite://")
    try:
        with engine.begin() as connection:
            connection.execute(sa.text("CREATE TABLE users (id INTEGER PRIMARY KEY)"))
            with pytest.raises(RuntimeError, match="partially populated"):
                run_migration(connection, baseline)
    finally:
        engine.dispose()


def test_doctor_link_migration_can_be_downgraded_on_sqlite():
    engine = create_engine("sqlite://")
    try:
        with engine.begin() as connection:
            run_migration(connection, baseline)
            run_migration(connection, doctor_link)
            doctor_link.downgrade()

        inspector = sa.inspect(engine)
        doctor_columns = {column["name"] for column in inspector.get_columns("doctors")}
        assert "user_id" not in doctor_columns
        assert not any(
            index.get("column_names") == ["user_id"]
            for index in inspector.get_indexes("doctors")
        )
        assert not any(
            foreign_key.get("constrained_columns") == ["user_id"]
            and foreign_key.get("referred_table") == "users"
            for foreign_key in inspector.get_foreign_keys("doctors")
        )
    finally:
        engine.dispose()
