from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "7f2dc8f87199"
down_revision: Union[str, Sequence[str], None] = "f151f0d1ce55"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "doctors",
        sa.Column("user_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_doctors_user_id",
        "doctors",
        ["user_id"],
        unique=True,
    )
    op.create_foreign_key(
        "fk_doctors_user_id_users",
        "doctors",
        "users",
        ["user_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_doctors_user_id_users",
        "doctors",
        type_="foreignkey",
    )
    op.drop_index("ix_doctors_user_id", table_name="doctors")
    op.drop_column("doctors", "user_id")
