"""Admin api schema."""

from decimal import Decimal
from enum import auto
from typing import Annotated, Any
from uuid import UUID

from pydantic import AwareDatetime, Field

from app.constants import (
    D0,
    D1,
    AccountType,
    ServiceSubtype,
    ServiceType,
    TransactionType,
)
from app.enum import HyphenStrEnum
from app.schema.api import AddPriceBase, PriceTierOut
from app.schema.common import BaseModel, FormattedDecimal


class AdminJobStatus(HyphenStrEnum):
    """Job status filter for the admin job list."""

    OPEN = auto()
    FINISHED = auto()
    CANCELLED = auto()


class AdminAccountOut(BaseModel):
    """AdminAccountOut."""

    id: UUID
    account_type: AccountType
    parent_id: UUID | None
    name: str
    balance: FormattedDecimal
    enabled: bool
    created_at: AwareDatetime
    updated_at: AwareDatetime


class AdminVlabOut(BaseModel):
    """AdminVlabOut."""

    id: UUID
    name: str
    balance: FormattedDecimal
    enabled: bool
    created_at: AwareDatetime
    updated_at: AwareDatetime


class AdminProjOut(BaseModel):
    """AdminProjOut."""

    id: UUID
    vlab_id: UUID
    name: str
    balance: FormattedDecimal
    reservation: FormattedDecimal
    enabled: bool
    created_at: AwareDatetime
    updated_at: AwareDatetime


class AdminAccountUpdateIn(BaseModel):
    """AdminAccountUpdateIn."""

    enabled: bool


class AdminAccountStatusOut(BaseModel):
    """Returned after enabling or disabling an account.

    `accounts` contains every account whose enabled flag was set, including the
    cascaded children. `open_job_ids` lists the still-open jobs charging the
    disabled accounts, as a warning to the operator; it is empty when enabling.
    """

    accounts: list[AdminAccountOut]
    open_job_ids: list[UUID]


class AdminLedgerEntryOut(BaseModel):
    """One side of a double-entry transaction."""

    id: int
    account_id: UUID
    account_name: str
    account_type: AccountType
    amount: FormattedDecimal


class AdminJournalOut(BaseModel):
    """A journal entry with its balanced ledger sides."""

    id: int
    transaction_datetime: AwareDatetime
    transaction_type: TransactionType
    job_id: UUID | None
    price_id: int | None
    discount_id: int | None
    properties: dict[str, Any] | None
    ledgers: list[AdminLedgerEntryOut]


class AdminJobOut(BaseModel):
    """AdminJobOut."""

    id: UUID
    group_id: UUID | None
    vlab_id: UUID
    proj_id: UUID
    name: str | None
    user_id: UUID | None
    service_type: ServiceType
    service_subtype: ServiceSubtype
    created_at: AwareDatetime
    updated_at: AwareDatetime
    reserved_at: AwareDatetime | None
    started_at: AwareDatetime | None
    last_alive_at: AwareDatetime | None
    last_charged_at: AwareDatetime | None
    finished_at: AwareDatetime | None
    cancelled_at: AwareDatetime | None
    reservation_params: dict[str, Any]
    usage_params: dict[str, Any]


class AdminJobDetailOut(AdminJobOut):
    """A job with its full journal trail and charge totals."""

    journal: list[AdminJournalOut]
    total_charged: FormattedDecimal
    total_refunded: FormattedDecimal
    remaining_reservation: FormattedDecimal


class AdminPriceOut(AddPriceBase):
    """AdminPriceOut."""

    id: int
    tiers: list[PriceTierOut]
    created_at: AwareDatetime
    updated_at: AwareDatetime


class AdminPriceExpireIn(BaseModel):
    """AdminPriceExpireIn."""

    valid_to: AwareDatetime | None = None


class AdminDiscountUpdateIn(BaseModel):
    """Partial update of a discount. Omitted fields are left unchanged."""

    discount: Annotated[Decimal, Field(ge=D0, le=D1)] | None = None
    valid_from: AwareDatetime | None = None
    valid_to: AwareDatetime | None = None


class AdminRefundIn(BaseModel):
    """AdminRefundIn."""

    job_id: UUID
    amount: Annotated[Decimal, Field(gt=D0)]
    reason: str | None = None


class AdminRefundOut(BaseModel):
    """AdminRefundOut."""

    journal_id: int
    job_id: UUID
    vlab_id: UUID
    proj_id: UUID
    amount: FormattedDecimal
