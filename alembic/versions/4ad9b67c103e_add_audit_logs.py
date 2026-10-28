"""Add metadata-only audit logs.

Revision ID: 4ad9b67c103e
Revises: c84a3d91f027
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "4ad9b67c103e"
down_revision: Union[str, Sequence[str], None] = "c84a3d91f027"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if "audit_logs" in sa.inspect(bind).get_table_names():
        return
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("resource_type", sa.String(length=80), nullable=False),
        sa.Column("resource_id", sa.String(length=80), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_logs_id", "audit_logs", ["id"], unique=False)
    op.create_index("ix_audit_logs_actor_user_id", "audit_logs", ["actor_user_id"], unique=False)
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"], unique=False)
    op.create_index("ix_audit_logs_actor_created", "audit_logs", ["actor_user_id", "created_at"], unique=False)
    op.create_index("ix_audit_logs_resource", "audit_logs", ["resource_type", "resource_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    if "audit_logs" not in sa.inspect(bind).get_table_names():
        return
    op.drop_index("ix_audit_logs_resource", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_created", table_name="audit_logs")
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_user_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_id", table_name="audit_logs")
    op.drop_table("audit_logs")
