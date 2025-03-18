"""Queue schema."""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field

from app.constants import LongrunStatus, ServiceSubtype, ServiceType
from app.schema.common import BaseModel, RecentTimeStamp


class StorageEvent(BaseModel):
    """StorageEvent."""

    type: Literal[ServiceType.STORAGE]
    subtype: Literal[ServiceSubtype.STORAGE] = ServiceSubtype.STORAGE
    proj_id: UUID
    size: Annotated[int, Field(ge=0)]
    timestamp: RecentTimeStamp


class OneshotEvent(BaseModel):
    """OneshotEvent."""

    type: Literal[ServiceType.ONESHOT]
    subtype: ServiceSubtype
    proj_id: UUID
    job_id: UUID
    name: str | None = None
    count: Annotated[int, Field(ge=0)]
    timestamp: RecentTimeStamp


class LongrunEvent(BaseModel):
    """LongrunEvent."""

    type: Literal[ServiceType.LONGRUN]
    subtype: ServiceSubtype
    proj_id: UUID
    job_id: UUID
    name: str | None = None
    status: LongrunStatus
    instances: Annotated[int | None, Field(ge=0)] = None
    instance_type: str | None = None
    timestamp: RecentTimeStamp
