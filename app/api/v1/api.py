from fastapi import APIRouter
from .endpoints import opsramp, topdesk

router = APIRouter()

router.include_router(opsramp.router, prefix="/opsramp", tags=["opsramp"])
router.include_router(topdesk.router, prefix="/topdesk", tags=["topdesk"])