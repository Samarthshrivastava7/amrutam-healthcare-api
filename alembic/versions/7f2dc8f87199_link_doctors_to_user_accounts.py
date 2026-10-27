"""Link doctor profiles to login accounts.

Revision ID: 7f2dc8f87199
Revises: f151f0d1ce55
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "7f2dc8f87199"
down_revision: Union[str, Sequence[str], None] = "f151f0d1ce55"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _doctor_user_foreign_keys(inspector):
    return [
        item
        for item in inspector.get_foreign_keys("doctors")
        if item.get("constrained_columns") == ["user_id"]
        and item.get("referred_table") == "users"
        and item.get("referred_columns") == ["id"]
    ]


def upgrade() -> None:
    """Add the doctor-account link without duplicating existing schema objects."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if not {"users", "doctors"}.issubset(tables):
        raise RuntimeError(
            "Cannot link doctor accounts: users and doctors tables must exist. "
            "Inspect the database schema before retrying the migration."
        )

    doctor_columns = {
        column["name"] for column in inspector.get_columns("doctors")
    }
    if "user_id" not in doctor_columns:
        op.add_column(
            "doctors",
            sa.Column("user_id", sa.Integer(), nullable=True),
        )

    # Re-inspect after possible DDL changes; the old Inspector is a snapshot.
    inspector = sa.inspect(bind)
    indexes = inspector.get_indexes("doctors")
    user_id_indexes = [
        index
        for index in indexes
        if index.get("column_names") == ["user_id"]
    ]
    unique_constraints = inspector.get_unique_constraints("doctors")
    has_unique_user_id_constraint = any(
        constraint.get("column_names") == ["user_id"]
        for constraint in unique_constraints
    )
    has_unique_user_id_index = any(
        index.get("unique") for index in user_id_indexes
    )

    if user_id_indexes and not has_unique_user_id_index:
        raise RuntimeError(
            "The doctors.user_id index exists but is not unique. "
            "Resolve the existing index manually before retrying."
        )

    if not has_unique_user_id_index and not has_unique_user_id_constraint:
        op.create_index(
            "ix_doctors_user_id",
            "doctors",
            ["user_id"],
            unique=True,
        )

    inspector = sa.inspect(bind)
    if not _doctor_user_foreign_keys(inspector):
        if bind.dialect.name == "sqlite":
            # SQLite cannot add a foreign-key constraint with ALTER TABLE.
            with op.batch_alter_table("doctors") as batch_op:
                batch_op.create_foreign_key(
                    "fk_doctors_user_id_users",
                    "users",
                    ["user_id"],
                    ["id"],
                )
        else:
            op.create_foreign_key(
                "fk_doctors_user_id_users",
                "doctors",
                "users",
                ["user_id"],
                ["id"],
            )


def downgrade() -> None:
    """Remove the doctor-account link when rolling back this revision."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "doctors" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("doctors")}
    if "user_id" not in columns:
        return

    foreign_keys = _doctor_user_foreign_keys(inspector)
    user_id_indexes = [
        index
        for index in inspector.get_indexes("doctors")
        if index.get("column_names") == ["user_id"]
    ]

    if bind.dialect.name == "sqlite":
        # Drop independent indexes before SQLite rebuilds the table; the rebuild
        # may remove indexed columns and the associated indexes.
        for index in user_id_indexes:
            if index.get("name"):
                op.drop_index(index["name"], table_name="doctors")
        with op.batch_alter_table("doctors") as batch_op:
            if foreign_keys and foreign_keys[0].get("name"):
                batch_op.drop_constraint(
                    foreign_keys[0]["name"],
                    type_="foreignkey",
                )
            batch_op.drop_column("user_id")
        return

    for foreign_key in foreign_keys:
        if foreign_key.get("name"):
            op.drop_constraint(
                foreign_key["name"],
                "doctors",
                type_="foreignkey",
            )

    for index in user_id_indexes:
        if index.get("name"):
            op.drop_index(index["name"], table_name="doctors")

    op.drop_column("doctors", "user_id")
