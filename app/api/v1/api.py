from fastapi import APIRouter
from .endpoints import opsramp, topdesk, monitoring

router = APIRouter()

router.include_router(opsramp.router, prefix="/opsramp", tags=["opsramp"])
router.include_router(topdesk.router, prefix="/topdesk", tags=["topdesk"])
router.include_router(monitoring.router, prefix="/monitoring", tags=["monitoring"])