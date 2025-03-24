"""Web api."""

from fastapi import APIRouter

from app.api import account, balance, budget, discount, price, report, reservation, root, usage

router = APIRouter()
router.include_router(root.router)
router.include_router(account.router, prefix="/account", tags=["account"])
router.include_router(balance.router, prefix="/balance", tags=["balance"])
router.include_router(budget.router, prefix="/budget", tags=["budget"])
router.include_router(discount.router, prefix="/discount", tags=["discount"])
router.include_router(price.router, prefix="/price", tags=["price"])
router.include_router(report.router, prefix="/report", tags=["report"])
router.include_router(reservation.router, prefix="/reservation", tags=["reservation"])
router.include_router(usage.router, prefix="/usage", tags=["usage"])
