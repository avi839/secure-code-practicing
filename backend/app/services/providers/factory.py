"""
Provider selection with explicit, recorded demo fallback (decision D14).
"""

from typing import Dict, List, Optional, Tuple

from app.config import settings
from app.services.providers.anthropic_provider import AnthropicProvider
from app.services.providers.base import AIProvider
from app.services.providers.demo import DEMO_MODEL, DemoProvider
from app.services.providers.gemini_provider import GeminiProvider
from app.services.providers.openai_provider import OpenAIProvider

# provider id -> (class, settings key attribute, model settings attribute, label)
_PROVIDERS = {
    "openai": (OpenAIProvider, "OPENAI_API_KEY", "OPENAI_MODEL", "OpenAI"),
    "anthropic": (AnthropicProvider, "ANTHROPIC_API_KEY", "ANTHROPIC_MODEL", "Anthropic"),
    "google": (GeminiProvider, "GOOGLE_API_KEY", "GEMINI_MODEL", "Google Gemini"),
}


def _value(requested) -> str:
    return str(getattr(requested, "value", requested) or "demo").lower()


def get_provider(requested, model: Optional[str] = None, transport=None) -> Tuple[AIProvider, Optional[str]]:
    """
    Return (provider, fallback_reason). fallback_reason is None when the requested
    provider is used as-is.
    """
    requested = _value(requested)
    if requested == "demo":
        return DemoProvider(model if model else None), None
    if requested not in _PROVIDERS:
        return DemoProvider(), f"Unknown provider '{requested}'"
    if settings.DEMO_MODE:
        return DemoProvider(), "DEMO_MODE is enabled"

    cls, key_attr, model_attr, _label = _PROVIDERS[requested]
    api_key = getattr(settings, key_attr)
    if not api_key:
        return DemoProvider(), f"{key_attr} is not configured"
    return cls(api_key=api_key, model=model or getattr(settings, model_attr), transport=transport), None


def provider_status() -> List[Dict]:
    """Safe-to-expose provider overview (never includes keys)."""
    providers = []
    for provider_id, (_cls, key_attr, model_attr, label) in _PROVIDERS.items():
        configured = bool(getattr(settings, key_attr))
        if settings.DEMO_MODE:
            effective = "demo-forced"
        elif configured:
            effective = "live"
        else:
            effective = "demo-fallback"
        providers.append(
            {
                "id": provider_id,
                "label": label,
                "configured": configured,
                "default_model": getattr(settings, model_attr),
                "effective": effective,
            }
        )
    providers.append(
        {"id": "demo", "label": "Demo (offline)", "configured": True, "default_model": DEMO_MODEL, "effective": "live"}
    )
    return providers
