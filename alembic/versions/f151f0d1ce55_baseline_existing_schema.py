"""Baseline schema for fresh databases; preserve existing application schemas.

Revision ID: f151f0d1ce55
Revises:
Create Date: 2026-10-26 20:11:37.427373
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f151f0d1ce55"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APPLICATION_TABLES = {
    "users",
    "doctors",
    "appointments",
    "consultations",
    "prescriptions",
}


def upgrade() -> None:
    """Create the initial schema only when no application tables exist."""
    bind = op.get_bind()
    existing_tables = set(sa.inspect(bind).get_table_names())
    existing_application_tables = existing_tables & APPLICATION_TABLES

    if existing_application_tables == APPLICATION_TABLES:
        # A legacy schema already exists; the next revision reconciles doctor linkage.
        return

    if existing_application_tables:
        missing = sorted(APPLICATION_TABLES - existing_application_tables)
        found = sorted(existing_application_tables)
        raise RuntimeError(
            "Refusing to initialize a partially populated Amrutam schema. "
            f"Found application tables: {found}; missing: {missing}. "
            "Back up the database and reconcile its schema before migrating."
        )

    # This revision intentionally models the pre-doctor-link schema. The next
    # revision adds doctors.user_id, keeping a single migration path for fresh
    # databases and existing installations.
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "role",
            sa.Enum("PATIENT", "DOCTOR", "ADMIN", name="userrole"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_users_id", "users", ["id"], unique=False)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "doctors",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("specialization", sa.String(length=120), nullable=False),
        sa.Column("qualifications", sa.String(length=255), nullable=False),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_doctors_id", "doctors", ["id"], unique=False)
    op.create_index(
        "ix_doctors_specialization",
        "doctors",
        ["specialization"],
        unique=False,
    )

    op.create_table(
        "appointments",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("doctor_id", sa.Integer(), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status",
            sa.Enum("BOOKED", "CANCELLED", "COMPLETED", name="appointmentstatus"),
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["patient_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["doctor_id"], ["doctors.id"]),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index("ix_appointments_id", "appointments", ["id"], unique=False)
    op.create_index(
        "ix_appointments_patient_id", "appointments", ["patient_id"], unique=False
    )
    op.create_index(
        "ix_appointments_doctor_id", "appointments", ["doctor_id"], unique=False
    )
    op.create_index(
        "ix_appointments_scheduled_at",
        "appointments",
        ["scheduled_at"],
        unique=False,
    )

    op.create_table(
        "consultations",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("appointment_id", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["appointment_id"], ["appointments.id"]),
        sa.UniqueConstraint("appointment_id"),
    )
    op.create_index("ix_consultations_id", "consultations", ["id"], unique=False)

    op.create_table(
        "prescriptions",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("consultation_id", sa.Integer(), nullable=False),
        sa.Column("medication_details", sa.Text(), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["consultation_id"], ["consultations.id"]),
    )
    op.create_index("ix_prescriptions_id", "prescriptions", ["id"], unique=False)
    op.create_index(
        "ix_prescriptions_consultation_id",
        "prescriptions",
        ["consultation_id"],
        unique=False,
    )


def downgrade() -> None:
    """Keep the baseline non-destructive for databases that predate Alembic."""
    # Deliberately do not drop application tables at the baseline revision:
    # those tables may be legacy data rather than tables created by this migration.
    pass
