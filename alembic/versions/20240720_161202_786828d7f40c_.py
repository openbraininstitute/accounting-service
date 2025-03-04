"""empty message

Revision ID: 786828d7f40c
Revises: d4a234cc39b4
Create Date: 2024-07-20 16:12:02.401612

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "786828d7f40c"
down_revision: str | None = "d4a234cc39b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_index(
        "only_one_system_account",
        "account",
        ["account_type"],
        unique=True,
        postgresql_where=sa.text("account_type = 'SYS'"),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(
        "only_one_system_account",
        table_name="account",
        postgresql_where=sa.text("account_type = 'SYS'"),
    )
    # ### end Alembic commands ###
