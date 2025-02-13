"""empty message

Revision ID: b974ebded6ab
Revises: 8bda482e60ef
Create Date: 2025-02-13 11:35:43.996036

"""

from collections.abc import Sequence

from alembic_postgresql_enum import TableReference

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b974ebded6ab"
down_revision: str | None = "8bda482e60ef"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.sync_enum_values(
        "public",
        "servicesubtype",
        ["STORAGE", "SINGLE_CELL_SIM", "SYNAPTOME_SIM", "ML_RETRIEVAL", "ML_LLM", "ML_RAG"],
        [
            TableReference(table_schema="public", table_name="job", column_name="service_subtype"),
            TableReference(
                table_schema="public", table_name="price", column_name="service_subtype"
            ),
        ],
        enum_values_to_rename=[],
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.sync_enum_values(
        "public",
        "servicesubtype",
        ["STORAGE", "SINGLE_CELL_SIM", "ML_RETRIEVAL", "ML_LLM", "ML_RAG"],
        [
            TableReference(table_schema="public", table_name="job", column_name="service_subtype"),
            TableReference(
                table_schema="public", table_name="price", column_name="service_subtype"
            ),
        ],
        enum_values_to_rename=[],
    )
    # ### end Alembic commands ###
