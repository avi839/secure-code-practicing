"""
Settings endpoint - read-only view of the safe-to-expose configuration.
Runtime mutation was removed: there is no authentication (decision D15).
"""

from typing import Dict, List

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.health import scanner_status
from app.config import settings
from app.services.providers import provider_status

router = APIRouter()

SUPPORTED_LANGUAGES = ["c", "cpp", "csharp", "java", "javascript", "python", "php", "rust"]


class ProviderInfo(BaseModel):
    id: str
    label: str
    configured: bool
    default_model: str
    effective: str


class RoundsInfo(BaseModel):
    min: int
    max: int
    default: int


class LimitsInfo(BaseModel):
    max_code_chars: int
    max_task_chars: int


class SettingsResponse(BaseModel):
    """Current application settings (safe to expose)"""
    environment: str
    demo_mode: bool
    default_ai_provider: str
    providers: List[ProviderInfo]
    scanners: Dict[str, str]
    supported_languages: List[str]
    ai_providers: Dict[str, bool]  # legacy shape used by the static pages
    rounds: RoundsInfo
    limits: LimitsInfo


@router.get("", response_model=SettingsResponse)
async def get_settings():
    """
    Get current application settings
    """
    return SettingsResponse(
        environment=settings.ENVIRONMENT,
        demo_mode=settings.DEMO_MODE,
        default_ai_provider=settings.DEFAULT_AI_PROVIDER,
        providers=[ProviderInfo(**p) for p in provider_status()],
        scanners=scanner_status(),
        supported_languages=SUPPORTED_LANGUAGES,
        ai_providers={
            "openai": bool(settings.OPENAI_API_KEY),
            "anthropic": bool(settings.ANTHROPIC_API_KEY),
            "google": bool(settings.GOOGLE_API_KEY),
            "demo": True,
        },
        rounds=RoundsInfo(min=1, max=10, default=settings.DEFAULT_REFLEXION_ROUNDS),
        limits=LimitsInfo(max_code_chars=settings.MAX_CODE_CHARS, max_task_chars=settings.MAX_TASK_CHARS),
    )
