"""DB Models."""

from datetime import datetime
from decimal import Decimal
from typing import ClassVar
from uuid import UUID

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Identity,
    Index,
    MetaData,
    SmallInteger,
    func,
    text,
    true,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.constants import AccountType, EventStatus, ServiceSubtype, ServiceType, TransactionType
from app.db.types import BIGINT, CREATED_AT, JSON_DICT, UPDATED_AT


class Base(DeclarativeBase):
    """Base class."""

    type_annotation_map: ClassVar[dict] = {
        datetime: DateTime(timezone=True),
    }
    # See https://alembic.sqlalchemy.org/en/latest/naming.html
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


class Event(Base):
    """Queue events table."""

    __tablename__ = "event"

    id: Mapped[BIGINT] = mapped_column(Identity(), primary_key=True)
    message_id: Mapped[UUID] = mapped_column(index=True, unique=True)
    queue_name: Mapped[str]
    status: Mapped[EventStatus]
    attributes: Mapped[JSON_DICT]
    body: Mapped[str | None]
    error: Mapped[str | None]
    job_id: Mapped[UUID | None] = mapped_column(ForeignKey("job.id"), index=True)
    counter: Mapped[int] = mapped_column(SmallInteger)
    created_at: Mapped[CREATED_AT]
    updated_at: Mapped[UPDATED_AT]


class Job(Base):
    """Job table."""

    __tablename__ = "job"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    group_id: Mapped[UUID | None]
    vlab_id: Mapped[UUID] = mapped_column(ForeignKey("account.id"), index=True)
    proj_id: Mapped[UUID] = mapped_column(ForeignKey("account.id"), index=True)
    name: Mapped[str | None]
    user_id: Mapped[UUID | None]
    service_type: Mapped[ServiceType]
    service_subtype: Mapped[ServiceSubtype]
    created_at: Mapped[CREATED_AT]
    updated_at: Mapped[UPDATED_AT]
    reserved_at: Mapped[datetime | None]
    started_at: Mapped[datetime | None]
    last_alive_at: Mapped[datetime | None]
    last_charged_at: Mapped[datetime | None]
    finished_at: Mapped[datetime | None]
    cancelled_at: Mapped[datetime | None]
    reservation_params: Mapped[JSON_DICT] = mapped_column(server_default="{}")
    usage_params: Mapped[JSON_DICT] = mapped_column(server_default="{}")


class Account(Base):
    """Account table."""

    __tablename__ = "account"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    account_type: Mapped[AccountType]
    parent_id: Mapped[UUID | None] = mapped_column(ForeignKey("account.id"), index=True)
    name: Mapped[str]
    balance: Mapped[Decimal] = mapped_column(server_default=text("0"))
    enabled: Mapped[bool] = mapped_column(server_default=true())
    created_at: Mapped[CREATED_AT]
    updated_at: Mapped[UPDATED_AT]


class Journal(Base):
    """Journal table."""

    __tablename__ = "journal"

    id: Mapped[BIGINT] = mapped_column(Identity(), primary_key=True)
    transaction_datetime: Mapped[datetime]
    transaction_type: Mapped[TransactionType]
    job_id: Mapped[UUID | None] = mapped_column(ForeignKey("job.id"), index=True)
    price_id: Mapped[BIGINT | None] = mapped_column(ForeignKey("price.id"), index=True)
    discount_id: Mapped[BIGINT | None] = mapped_column(ForeignKey("discount.id"), index=True)
    properties: Mapped[JSON_DICT | None]
    created_at: Mapped[CREATED_AT]


class Ledger(Base):
    """Ledger table."""

    __tablename__ = "ledger"

    id: Mapped[BIGINT] = mapped_column(Identity(), primary_key=True)
    account_id: Mapped[UUID] = mapped_column(ForeignKey("account.id"), index=True)
    journal_id: Mapped[BIGINT] = mapped_column(ForeignKey("journal.id"), index=True)
    amount: Mapped[Decimal]
    created_at: Mapped[CREATED_AT]


class Price(Base):
    """Price table."""

    __tablename__ = "price"

    id: Mapped[BIGINT] = mapped_column(Identity(), primary_key=True)
    service_type: Mapped[ServiceType]
    service_subtype: Mapped[ServiceSubtype] = mapped_column(index=True)
    valid_from: Mapped[datetime]
    valid_to: Mapped[datetime | None]
    fixed_cost: Mapped[Decimal]
    multiplier: Mapped[Decimal]
    vlab_id: Mapped[UUID | None] = mapped_column(ForeignKey("account.id"), index=True)
    created_at: Mapped[CREATED_AT]
    updated_at: Mapped[UPDATED_AT]


class Discount(Base):
    """Discount table."""

    __tablename__ = "discount"

    id: Mapped[BIGINT] = mapped_column(Identity(), primary_key=True)
    vlab_id: Mapped[UUID | None] = mapped_column(ForeignKey("account.id"), index=True)
    valid_from: Mapped[datetime] = mapped_column(default=func.now())
    valid_to: Mapped[datetime | None]
    discount: Mapped[Decimal]


Index(
    "only_one_system_account",
    Account.account_type,
    unique=True,
    postgresql_where=Account.account_type == AccountType.SYS,
)
