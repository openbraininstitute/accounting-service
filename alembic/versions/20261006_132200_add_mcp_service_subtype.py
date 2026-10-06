"""Add MCP notebook service subtype.

Revision ID: 6d7f8a9b0c1d
Revises: 84da22d3cd9e
Create Date: 2026-10-06 13:22:00.000000

"""

from collections.abc import Sequence

from alembic_postgresql_enum import TableReference

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6d7f8a9b0c1d"
down_revision: str | None = "84da22d3cd9e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_SERVICE_SUBTYPES = [
    "ION_CHANNEL_BUILD",
    "ION_CHANNEL_SIM",
    "ML_LLM",
    "MCP",
    "NEURON_MESH_SKELETONIZATION",
    "NOTEBOOK",
    "SINGLE_CELL_BUILD",
    "SINGLE_CELL_SIM",
    "SMALL_CIRCUIT_SIM",
    "STORAGE",
    "SYNAPTOME_BUILD",
    "SYNAPTOME_SIM",
    "SINGLE_SIM",
    "PAIR_SIM",
    "SMALL_SIM",
    "MICROCIRCUIT_SIM",
    "REGION_SIM",
    "SYSTEM_SIM",
    "WHOLE_BRAIN_SIM",
    "CIRCUIT_EXTRACTION",
    "CIRCUIT_SIMPLIFICATION",
    "EM_SYNAPSE_MAPPING",
    "BRIAN2_CIRCUIT_SIMULATION",
    "EMODEL_FEATURES_EXTRACTION",
    "EMODEL_OPTIMISATION",
    "EMODEL_VALIDATION",
    "SYNAPSE_PARAMETERIZATION_SMALL",
    "SYNAPSE_PARAMETERIZATION_LARGE",
    "ML_RAG",
    "ML_RETRIEVAL",
]

_AFFECTED_COLUMNS = [
    TableReference(table_schema="public", table_name="job", column_name="service_subtype"),
    TableReference(table_schema="public", table_name="price", column_name="service_subtype"),
]


def upgrade() -> None:
    op.sync_enum_values(
        enum_schema="public",
        enum_name="servicesubtype",
        new_values=_SERVICE_SUBTYPES,
        affected_columns=_AFFECTED_COLUMNS,
        enum_values_to_rename=[],
    )


def downgrade() -> None:
    op.sync_enum_values(
        enum_schema="public",
        enum_name="servicesubtype",
        new_values=[value for value in _SERVICE_SUBTYPES if value != "MCP"],
        affected_columns=_AFFECTED_COLUMNS,
        enum_values_to_rename=[],
    )
