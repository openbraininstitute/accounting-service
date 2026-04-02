"""Add price_tier table and migrate data from price

Revision ID: 3642bb905be6
Revises: 75dc053ee063
Create Date: 2026-04-02 14:35:04.939626

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3642bb905be6"
down_revision: str | None = "75dc053ee063"
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
        sa.Column("base_cost", sa.Numeric(), nullable=False),
        sa.Column("multiplier", sa.Numeric(), nullable=False),
        sa.ForeignKeyConstraint(
            ["price_id"], ["price.id"], name=op.f("fk_price_tier_price_id_price")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_price_tier")),
    )
    op.create_index(op.f("ix_price_tier_price_id"), "price_tier", ["price_id"], unique=False)

    # Migrate existing price data into single-tier rows.
    # The old multiplier becomes the tier multiplier, base_cost is 0 since
    # there's only one tier. The old fixed_cost stays on the price table.
    op.execute(
        """
        INSERT INTO price_tier (price_id, min_quantity, max_quantity, base_cost, multiplier)
        SELECT id, 0, NULL, 0, multiplier
        FROM price
        """
    )

    # Drop the multiplier column from price (fixed_cost stays)
    op.drop_column("price", "multiplier")


def downgrade() -> None:
    # Re-add multiplier to price, initially nullable
    op.add_column(
        "price", sa.Column("multiplier", sa.NUMERIC(), autoincrement=False, nullable=True)
    )

    # Migrate multiplier back from the first tier
    op.execute(
        """
        UPDATE price
        SET multiplier = pt.multiplier
        FROM price_tier pt
        WHERE pt.price_id = price.id AND pt.min_quantity = 0
        """
    )

    # Set NOT NULL after populating
    op.alter_column("price", "multiplier", nullable=False)

    # Drop price_tier table
    op.drop_index(op.f("ix_price_tier_price_id"), table_name="price_tier")
    op.drop_table("price_tier")
