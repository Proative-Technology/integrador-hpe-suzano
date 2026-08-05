#import sys
#import pysqlite3
#sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
from app.api.v1.api import router as api_router
from app.config import settings
from starlette.middleware import Middleware
from app.middleware import LoggingMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import asyncio
import secrets
from app.models.dbinit import init_db
from app.health import check_db, check_topdesk, check_opsramp
from app.logger import logger



init_db()# Initialize the database



origins = [
    "https://login.microsoftonline.com",
    "*"
]

middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
        expose_headers=["Content-Type", "Authorization", "Set-Cookie", "Access-Control-Allow-Origin"],
    ),
    Middleware(
        SessionMiddleware,
        secret_key=secrets.token_urlsafe(32),
    ),

]


app = FastAPI(
    title="Integrador HPE",
    docs_url="/docs",
    openapi_url="/openapi.json",
    middleware=middleware,
    root_path=settings.root_path,
)

app.add_middleware(LoggingMiddleware)
# app.add_middleware(SessionMiddleware, secret_key=secrets.token_urlsafe(32))


@app.get("/health")
async def health():
    logger.info("Health check - start")
    try:
        loop = asyncio.get_event_loop()
        db, topdesk, opsramp = await asyncio.gather(
            loop.run_in_executor(None, check_db),
            loop.run_in_executor(None, check_topdesk),
            loop.run_in_executor(None, check_opsramp),
        )
        logger.info(f"Health check - results: db={db}, topdesk={topdesk}, opsramp={opsramp}")
        services = {"database": db, "topdesk": topdesk, "opsramp": opsramp}
        healthy = all(s["status"] == "ok" for s in services.values())
        code = 200 if healthy else 503
        logger.info(f"Health check - healthy={healthy}, code={code}")
        return JSONResponse(
            status_code=code,
            content={"status": "ok" if healthy else "degraded", "services": services},
        )
    except Exception as e:
        logger.exception(f"Health check - unhandled error: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "detail": str(e)},
        )

@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": exc.errors()})

app.include_router(api_router, prefix="/api")
