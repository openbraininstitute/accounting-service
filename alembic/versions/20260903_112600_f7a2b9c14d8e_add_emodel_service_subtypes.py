"""Add emodel building service subtypes

Revision ID: f7a2b9c14d8e
Revises: ec438a5524f8
Create Date: 2026-09-03 11:26:00.000000

"""

from collections.abc import Sequence

from alembic_postgresql_enum import TableReference

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f7a2b9c14d8e"
down_revision: str | None = "ec438a5524f8"
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
            "ML_RAG",
            "ML_RETRIEVAL",
        ],
        affected_columns=[
            TableReference(table_schema="public", table_name="job", column_name="service_subtype"),
            TableReference(
                table_schema="public", table_name="price", column_name="service_subtype"
            ),
        ],
        enum_values_to_rename=[],
    )


def downgrade() -> None:
    op.sync_enum_values(
        enum_schema="public",
        enum_name="servicesubtype",
        new_values=[
            "ION_CHANNEL_BUILD",
            "ION_CHANNEL_SIM",
            "ML_LLM",
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
            "ML_RAG",
            "ML_RETRIEVAL",
        ],
        affected_columns=[
            TableReference(table_schema="public", table_name="job", column_name="service_subtype"),
            TableReference(
                table_schema="public", table_name="price", column_name="service_subtype"
            ),
        ],
        enum_values_to_rename=[],
    )
