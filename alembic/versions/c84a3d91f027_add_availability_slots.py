"""Add doctor availability slots.

Revision ID: c84a3d91f027
Revises: 7f2dc8f87199
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c84a3d91f027"
down_revision: Union[str, Sequence[str], None] = "7f2dc8f87199"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if "availability_slots" in sa.inspect(bind).get_table_names():
        return
    op.create_table(
        "availability_slots",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("doctor_id", sa.Integer(), sa.ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("doctor_id", "starts_at", name="uq_availability_doctor_start"),
    )
    op.create_index("ix_availability_slots_id", "availability_slots", ["id"], unique=False)
    op.create_index("ix_availability_slots_doctor_id", "availability_slots", ["doctor_id"], unique=False)
    op.create_index("ix_availability_doctor_window", "availability_slots", ["doctor_id", "starts_at", "ends_at"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    if "availability_slots" not in sa.inspect(bind).get_table_names():
        return
    op.drop_index("ix_availability_doctor_window", table_name="availability_slots")
    op.drop_index("ix_availability_slots_doctor_id", table_name="availability_slots")
    op.drop_index("ix_availability_slots_id", table_name="availability_slots")
    op.drop_table("availability_slots")
