"""Add DEPLETE transaction type

Revision ID: a1b2c3d4e5f6
Revises: 8c8dc5fa244d
Create Date: 2026-06-12 10:30:00.000000

"""

from collections.abc import Sequence

from alembic_postgresql_enum import TableReference

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "8c8dc5fa244d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.sync_enum_values(
        "public",
        "transactiontype",
        [
            "TOP_UP",
            "ASSIGN_BUDGET",
            "REVERSE_BUDGET",
            "MOVE_BUDGET",
            "RESERVE",
            "RELEASE",
            "CHARGE_ONESHOT",
            "CHARGE_LONGRUN",
            "CHARGE_STORAGE",
            "REFUND",
            "DEPLETE",
        ],
        [
            TableReference(
                table_schema="public", table_name="journal", column_name="transaction_type"
            )
        ],
        enum_values_to_rename=[],
    )


def downgrade() -> None:
    op.sync_enum_values(
        "public",
        "transactiontype",
        [
            "TOP_UP",
            "ASSIGN_BUDGET",
            "REVERSE_BUDGET",
            "MOVE_BUDGET",
            "RESERVE",
            "RELEASE",
            "CHARGE_ONESHOT",
            "CHARGE_LONGRUN",
            "CHARGE_STORAGE",
            "REFUND",
        ],
        [
            TableReference(
                table_schema="public", table_name="journal", column_name="transaction_type"
            )
        ],
        enum_values_to_rename=[],
    )
