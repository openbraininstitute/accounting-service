"""Split REFUND into OVERCHARGE_REFUND and MANUAL_REFUND

Revision ID: b7c4e91d2a35
Revises: 1efdebc86af2
Create Date: 2026-08-25 10:45:00.000000

The existing REFUND rows are all automatic corrections written by
`charge_longrun`, so they are renamed to OVERCHARGE_REFUND. MANUAL_REFUND is
new and only written by `POST /admin/refund`, which is why the downgrade fails
if any MANUAL_REFUND row exists: there is no value to map it back to.

"""

from collections.abc import Sequence

from alembic_postgresql_enum import TableReference

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7c4e91d2a35"
down_revision: str | None = "1efdebc86af2"
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
            "OVERCHARGE_REFUND",
            "MANUAL_REFUND",
            "DEPLETE",
        ],
        [
            TableReference(
                table_schema="public", table_name="journal", column_name="transaction_type"
            )
        ],
        enum_values_to_rename=[("REFUND", "OVERCHARGE_REFUND")],
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
            "DEPLETE",
        ],
        [
            TableReference(
                table_schema="public", table_name="journal", column_name="transaction_type"
            )
        ],
        enum_values_to_rename=[("OVERCHARGE_REFUND", "REFUND")],
    )
