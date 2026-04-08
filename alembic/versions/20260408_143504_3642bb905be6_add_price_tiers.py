"""Add price_tier table, migrate data from price, remove price.fixed_cost

Revision ID: 3642bb905be6
Revises: 590072d41213
Create Date: 2026-04-08 14:35:04.939626

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3642bb905be6"
down_revision: str | None = "590072d41213"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create price_tier table
    op.create_table(
        "price_tier",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("price_id", sa.BigInteger(), nullable=False),
        sa.Column("min_quantity", sa.Integer(), nullable=False),
        sa.Column("max_quantity", sa.Integer(), nullable=True),
        sa.Column("fixed_cost", sa.Numeric(), nullable=False),
        sa.Column("multiplier", sa.Numeric(), nullable=False),
        sa.ForeignKeyConstraint(
            ["price_id"], ["price.id"], name=op.f("fk_price_tier_price_id_price")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_price_tier")),
    )
    op.create_index(op.f("ix_price_tier_price_id"), "price_tier", ["price_id"], unique=False)

    # Migrate existing price data into single-tier rows.
    # The old price.multiplier becomes the tier multiplier.
    # The old price.fixed_cost becomes the tier fixed_cost.
    op.execute(
        """
        INSERT INTO price_tier (price_id, min_quantity, max_quantity, fixed_cost, multiplier)
        SELECT id, 0, NULL, fixed_cost, multiplier
        FROM price
        """
    )

    op.drop_column("price", "multiplier")
    op.drop_column("price", "fixed_cost")


def downgrade() -> None:
    # Re-add columns to price, initially nullable
    op.add_column(
        "price", sa.Column("multiplier", sa.NUMERIC(), autoincrement=False, nullable=True)
    )
    op.add_column(
        "price", sa.Column("fixed_cost", sa.NUMERIC(), autoincrement=False, nullable=True)
    )

    # Migrate back from the first tier
    op.execute(
        """
        UPDATE price
        SET multiplier = pt.multiplier, fixed_cost = pt.fixed_cost
        FROM price_tier pt
        WHERE pt.price_id = price.id AND pt.min_quantity = 0
        """
    )

    # Set NOT NULL after populating
    op.alter_column("price", "multiplier", nullable=False)
    op.alter_column("price", "fixed_cost", nullable=False)

    # Drop price_tier table
    op.drop_index(op.f("ix_price_tier_price_id"), table_name="price_tier")
    op.drop_table("price_tier")
