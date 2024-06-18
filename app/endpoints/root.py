"""Root endpoints."""

from fastapi import APIRouter
from starlette.responses import RedirectResponse, Response
from starlette.status import HTTP_302_FOUND

from app.config import settings
from app.errors import ApiError

router = APIRouter()


@router.get("/")
async def root() -> Response:
    """Root endpoint."""
    return RedirectResponse(url="/docs", status_code=HTTP_302_FOUND)


@router.get("/health")
async def health() -> dict:
    """Health endpoint."""
    return {
        "status": "OK",
    }


@router.get("/version")
async def version() -> dict:
    """Version endpoint."""
    return {
        "app_name": settings.APP_NAME,
        "app_version": settings.APP_VERSION,
        "commit_sha": settings.COMMIT_SHA,
    }


@router.get("/error", include_in_schema=False)
async def error() -> None:
    """Error endpoint to test generic error responses."""
    msg = "Generic error returned for testing purposes"
    raise ApiError(msg)
