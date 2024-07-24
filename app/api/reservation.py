"""Reservation api."""

from fastapi import APIRouter

from app.dependencies import RepoGroupDep
from app.schema.api import (
    LongJobReservationRequest,
    ReservationResponse,
    ShortJobReservationRequest,
)
from app.service import reservation

router = APIRouter()


@router.post("/short-job")
async def make_short_job_reservation(
    repos: RepoGroupDep,
    reservation_request: ShortJobReservationRequest,
) -> ReservationResponse:
    """Make a new reservation for a short job."""
    return await reservation.make_short_job_reservation(repos, reservation_request)


@router.post("/long-job")
async def make_long_job_reservation(
    repos: RepoGroupDep,
    reservation_request: LongJobReservationRequest,
) -> ReservationResponse:
    """Make a new reservation for a long job."""
    return await reservation.make_long_job_reservation(repos, reservation_request)
