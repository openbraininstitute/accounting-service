"""Split CIRCUIT_SIMPLIFICATION into SMALL/MEDIUM/LARGE

Revision ID: c3f8a1e92b47
Revises: 33531e21bbaa
Create Date: 2026-11-12 11:52:00.000000

Existing CIRCUIT_SIMPLIFICATION rows (jobs and prices) are renamed to
CIRCUIT_SIMPLIFICATION_SMALL. MEDIUM and LARGE are new.

"""

from collections.abc import Sequence

from alembic_postgresql_enum import TableReference

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3f8a1e92b47"
down_revision: str | None = "33531e21bbaa"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.sync_enum_values(
        enum_schema="public",
        enum_name="servicesubtype",
        new_values=[
            "ION_CHANNEL_BUILD",
            "ION_CHANNEL_SIM",
            "ML_LLM",
            "MCP",
            "RESEARCH_AGENT",
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
            "CIRCUIT_SIMPLIFICATION_SMALL",
            "CIRCUIT_SIMPLIFICATION_MEDIUM",
            "CIRCUIT_SIMPLIFICATION_LARGE",
            "EM_SYNAPSE_MAPPING",
            "BRIAN2_CIRCUIT_SIMULATION",
            "NEST_CIRCUIT_SIMULATION",
            "EMODEL_FEATURES_EXTRACTION",
            "EMODEL_OPTIMISATION",
            "EMODEL_VALIDATION",
            "SYNAPSE_PARAMETERIZATION_SMALL",
            "SYNAPSE_PARAMETERIZATION_LARGE",
            "EXTRACELLULAR_RECORDING_ARRAY_BUILD",
            "ML_RAG",
            "ML_RETRIEVAL",
        ],
        affected_columns=[
            TableReference(table_schema="public", table_name="job", column_name="service_subtype"),
            TableReference(
                table_schema="public", table_name="price", column_name="service_subtype"
            ),
        ],
        enum_values_to_rename=[("CIRCUIT_SIMPLIFICATION", "CIRCUIT_SIMPLIFICATION_SMALL")],
    )


def downgrade() -> None:
    op.sync_enum_values(
        enum_schema="public",
        enum_name="servicesubtype",
        new_values=[
            "ION_CHANNEL_BUILD",
            "ION_CHANNEL_SIM",
            "ML_LLM",
            "MCP",
            "RESEARCH_AGENT",
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
            "NEST_CIRCUIT_SIMULATION",
            "EMODEL_FEATURES_EXTRACTION",
            "EMODEL_OPTIMISATION",
            "EMODEL_VALIDATION",
            "SYNAPSE_PARAMETERIZATION_SMALL",
            "SYNAPSE_PARAMETERIZATION_LARGE",
            "EXTRACELLULAR_RECORDING_ARRAY_BUILD",
            "ML_RAG",
            "ML_RETRIEVAL",
        ],
        affected_columns=[
            TableReference(table_schema="public", table_name="job", column_name="service_subtype"),
            TableReference(
                table_schema="public", table_name="price", column_name="service_subtype"
            ),
        ],
        enum_values_to_rename=[("CIRCUIT_SIMPLIFICATION_SMALL", "CIRCUIT_SIMPLIFICATION")],
    )
