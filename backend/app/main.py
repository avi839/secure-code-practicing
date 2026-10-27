"""
FastAPI application entry point for SecureReflex AI
"""

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.database import AsyncSessionLocal, init_db
from app.logging_config import request_id_var, setup_logging
from app.api import evaluations, analytics, settings as settings_api, health, scan

setup_logging()
logger = logging.getLogger("app")

REQUEST_ID_HEADER = "X-Request-ID"
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    logger.info(
        "SecureReflex AI starting (environment=%s, demo_mode=%s, database=%s)",
        settings.ENVIRONMENT, settings.DEMO_MODE, settings.masked_database_url,
    )
    await init_db()
    # Seed the demo user once so concurrent first requests never race to create it.
    async with AsyncSessionLocal() as db:
        await evaluations.ensure_demo_user(db)
    yield
    logger.info("SecureReflex AI shutting down")


app = FastAPI(
    title="SecureReflex AI API",
    description="AI-assisted secure code generation with reflexion-based vulnerability repair",
    version=health.APP_VERSION,
    lifespan=lifespan,
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    """Assign a request id (or accept a sane client-provided one) and add security headers."""
    incoming = request.headers.get(REQUEST_ID_HEADER, "")
    request_id = incoming if 0 < len(incoming) <= 64 and incoming.replace("-", "").isalnum() else uuid.uuid4().hex
    token = request_id_var.set(request_id)
    request.state.request_id = request_id
    try:
        response = await call_next(request)
    finally:
        request_id_var.reset(token)
    response.headers[REQUEST_ID_HEADER] = request_id
    for name, value in SECURITY_HEADERS.items():
        response.headers.setdefault(name, value)
    return response


# CORS (the Next.js frontend uses a same-origin proxy; this is for direct API clients / legacy pages)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", REQUEST_ID_HEADER],
    expose_headers=[REQUEST_ID_HEADER],
)


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", None) or request_id_var.get()


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Never echo the submitted input back (it may contain code or secrets).
    errors = [
        {
            "field": ".".join(str(part) for part in error.get("loc", ())),
            "message": error.get("msg", "Invalid value"),
        }
        for error in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": "Validation failed", "errors": errors})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = _request_id(request)
    # ServerErrorMiddleware runs this after request_context has reset the contextvar,
    # so restore it for the log record and also put the id in the message itself.
    token = request_id_var.set(request_id)
    try:
        logger.exception(
            "Unhandled error on %s %s (request_id=%s)", request.method, request.url.path, request_id
        )
    finally:
        request_id_var.reset(token)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "request_id": request_id},
        headers={REQUEST_ID_HEADER: request_id, **SECURITY_HEADERS},
    )


# Include routers
app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(evaluations.router, prefix="/api/evaluations", tags=["Evaluations"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(settings_api.router, prefix="/api/settings", tags=["Settings"])
app.include_router(scan.router, prefix="/api", tags=["Scan"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "SecureReflex AI API",
        "version": health.APP_VERSION,
        "status": "running",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=settings.ENVIRONMENT == "development",
    )
