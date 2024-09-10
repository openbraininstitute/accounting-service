"""Domain entities."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from pydantic import ConfigDict, Field

from app.constants import D0, ServiceSubtype, ServiceType
from app.schema.common import BaseModel


class BaseAccount(BaseModel):
    """BaseAccount."""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    balance: Decimal = D0
    enabled: bool = True


class SysAccount(BaseAccount):
    """SysAccount."""


class VlabAccount(BaseAccount):
    """VlabAccount."""


class ProjAccount(BaseAccount):
    """ProjAccount."""

    vlab_id: Annotated[UUID, Field(alias="parent_id")]


class RsvAccount(BaseAccount):
    """RsvAccount."""

    proj_id: Annotated[UUID, Field(alias="parent_id")]


class Accounts(BaseModel):
    """Accounts."""

    sys: SysAccount
    vlab: VlabAccount
    proj: ProjAccount
    rsv: RsvAccount


class BaseJob(BaseModel):
    """BaseJob."""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    vlab_id: UUID
    proj_id: UUID
    service_type: ServiceType
    service_subtype: ServiceSubtype
    created_at: datetime
    reserved_at: datetime | None
    started_at: datetime | None
    last_alive_at: datetime | None
    last_charged_at: datetime | None
    finished_at: datetime | None
    reservation_params: dict[str, Any]
    usage_params: dict[str, Any]


class StartedJob(BaseJob):
    """StartedJob (finished or not)."""

    started_at: datetime
    last_alive_at: datetime


@dataclass(kw_only=True)
class TaskResult:
    """Result of a generic task."""

    success: int = 0
    failure: int = 0
    last_active_job: datetime | None = None

    def update_last_active_job(self, value: datetime | None) -> None:
        """Update last_active_job with the given value only if the new value is lower."""
        if not self.last_active_job or (value and value < self.last_active_job):
            self.last_active_job = value


@dataclass(kw_only=True)
class ChargeLongrunResult(TaskResult):
    """Result of charge_longrun."""

    unfinished_uncharged: int = 0
    unfinished_charged: int = 0
    finished_uncharged: int = 0
    finished_charged: int = 0
    finished_overcharged: int = 0
    expired_uncharged: int = 0
    expired_charged: int = 0


@dataclass(kw_only=True)
class ChargeOneshotResult(TaskResult):
    """Result of charge_oneshot."""


@dataclass(kw_only=True)
class ChargeStorageResult(TaskResult):
    """Result of charge_storage."""
