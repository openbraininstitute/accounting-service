"""Constants module."""

from decimal import Decimal
from enum import auto

from app.enum import HyphenStrEnum

D0 = Decimal(0)
D1 = Decimal(1)
DECIMAL_PLACES = 2


class EventStatus(HyphenStrEnum):
    """Queue Message Status."""

    COMPLETED = auto()
    FAILED = auto()


class ServiceType(HyphenStrEnum):
    """Service Type."""

    STORAGE = auto()
    ONESHOT = auto()
    LONGRUN = auto()


class LongrunStatus(HyphenStrEnum):
    """Longrun Status."""

    STARTED = auto()
    RUNNING = auto()
    FINISHED = auto()


class AccountType(HyphenStrEnum):
    """Account Type."""

    SYS = auto()
    VLAB = auto()
    PROJ = auto()
    RSV = auto()


class TransactionType(HyphenStrEnum):
    """Transaction Type."""

    TOP_UP = auto()  # from SYS to VLAB
    ASSIGN_BUDGET = auto()  # from VLAB to PROJ
    REVERSE_BUDGET = auto()  # from PROJ to VLAB
    MOVE_BUDGET = auto()  # from PROJ to PROJ
    RESERVE = auto()  # from PROJ to RSV
    RELEASE = auto()  # from RSV to PROJ
    CHARGE_ONESHOT = auto()  # from RSV to SYS, or from PROJ to SYS
    CHARGE_LONGRUN = auto()  # from RSV to SYS, or from PROJ to SYS
    CHARGE_STORAGE = auto()  # from RSV to SYS, or from PROJ to SYS
    REFUND = auto()  # from SYS to PROJ


class ServiceSubtype(HyphenStrEnum):
    """Service Subtype."""

    # Please report the repository and what the constant is used for

    # `neuroagent`; Used for `qa` chat agent
    ML_LLM = auto()
    ML_RAG = auto()
    ML_RETRIEVAL = auto()
    NEURON_MESH_SKELETONIZATION = auto()
    # `notebook-service`: Currently running notebook
    NOTEBOOK = auto()
    # `Bluenaas`: Create a single neuron model
    SINGLE_CELL_BUILD = auto()
    # `Bluenaas`: Run a single neuron simulation
    SINGLE_CELL_SIM = auto()
    # `Bluenaas`: Multi-neuron simulation
    SMALL_CIRCUIT_SIM = auto()
    STORAGE = auto()
    # `Bluenaas`: Single neuron synaptome
    SYNAPTOME_BUILD = auto()
    # `Bluenaas`: Single neuron synaptome simulation
    SYNAPTOME_SIM = auto()
