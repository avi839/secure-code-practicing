"""
Health check endpoint
"""

import logging
import sys

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.services.scanner.bandit_runner import bandit_available

logger = logging.getLogger(__name__)

router = APIRouter()

APP_VERSION = "1.0.0"


def scanner_status() -> dict:
    if not settings.BANDIT_ENABLED:
        bandit = "disabled"
    elif bandit_available():
        bandit = "available"
    else:
        bandit = "not_installed"
    return {"builtin": "available", "bandit": bandit, "semgrep": "not_integrated"}


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    System health check
    Returns status of key dependencies (never secrets or exception text)
    """
    health_status = {
        "status": "healthy",
        "version": APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "demo_mode": settings.DEMO_MODE,
        "components": {},
    }

    database = {"status": "healthy", "type": settings.database_backend}
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Database health check failed")
        health_status["status"] = "degraded"
        database = {
            "status": "unhealthy",
            "type": settings.database_backend,
            "message": "Database is unreachable; check DATABASE_URL and the server logs.",
        }
    health_status["components"]["database"] = database

    def provider(key) -> str:
        return "configured" if key else "not_configured"

    health_status["components"]["ai_providers"] = {
        "openai": provider(settings.OPENAI_API_KEY),
        "anthropic": provider(settings.ANTHROPIC_API_KEY),
        "google": provider(settings.GOOGLE_API_KEY),
        "demo": "available",
    }
    health_status["components"]["security_scanners"] = scanner_status()

    return health_status
