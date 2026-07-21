"""Admin web api for platform operators.

The `/admin` namespace is not authenticated: like the rest of this service, it
relies on the internal trust boundary, and it is expected to be exposed to
operators only through an authenticated proxy.
"""

from fastapi import APIRouter

from app.api.admin import account, discount, job, journal, price, refund

router = APIRouter()
router.include_router(account.router, prefix="/account", tags=["admin-account"])
router.include_router(journal.router, prefix="/journal", tags=["admin-journal"])
router.include_router(job.router, prefix="/job", tags=["admin-job"])
router.include_router(price.router, prefix="/price", tags=["admin-price"])
router.include_router(discount.router, prefix="/discount", tags=["admin-discount"])
router.include_router(refund.router, prefix="/refund", tags=["admin-refund"])
