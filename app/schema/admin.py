"""Admin api schema."""

from decimal import Decimal
from enum import auto
from typing import Annotated, Any, Self
from uuid import UUID

from pydantic import AwareDatetime, Field, model_validator

from app.constants import (
    D0,
    D1,
    AccountType,
    ServiceSubtype,
    ServiceType,
    TransactionType,
)
from app.enum import HyphenStrEnum
from app.schema.api import (
    AddPriceBase,
    PaginationQueryParams,
    PriceTierOut,
    StartedIntervalQueryParams,
)
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


class TransactionIntervalQueryParams(BaseModel):
    """Query parameters filtering by the interval when a transaction was recorded."""

    transaction_after: AwareDatetime | None = None
    transaction_before: AwareDatetime | None = None

    @model_validator(mode="after")
    def check_transaction_interval(self) -> Self:
        """Check that the interval is not empty."""
        if (
            self.transaction_after
            and self.transaction_before
            and self.transaction_after >= self.transaction_before
        ):
            err = "transaction_after must be before transaction_before"
            raise ValueError(err)
        return self


class AdminJournalQueryParams(PaginationQueryParams, TransactionIntervalQueryParams):
    """Query parameters of the admin journal endpoint."""

    account_id: UUID | None = None
    transaction_type: TransactionType | None = None
    job_id: UUID | None = None


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


class AdminJobQueryParams(PaginationQueryParams, StartedIntervalQueryParams):
    """Query parameters of the admin job endpoint."""

    vlab_id: UUID | None = None
    proj_id: UUID | None = None
    service_type: ServiceType | None = None
    service_subtype: ServiceSubtype | None = None
    status: AdminJobStatus | None = None


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
    amount: (
        Annotated[
            Decimal,
            Field(gt=D0, description="Amount to refund. If omitted, the whole job is refunded."),
        ]
        | None
    ) = None
    reason: str | None = None


class AdminRefundOut(BaseModel):
    """AdminRefundOut."""

    journal_id: int
    job_id: UUID
    vlab_id: UUID
    proj_id: UUID
    amount: FormattedDecimal
