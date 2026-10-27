"""Anthropic Messages API provider (plain httpx)."""

from typing import Any, Dict

from app.config import settings
from app.services.providers.base import HTTPProvider

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"


class AnthropicProvider(HTTPProvider):
    name = "anthropic"
    label = "Anthropic"

    def default_model(self) -> str:
        return settings.ANTHROPIC_MODEL

    def build_request(self, system: str, user: str) -> Dict[str, Any]:
        return {
            "url": ANTHROPIC_URL,
            "headers": {
                "x-api-key": self._api_key,
                "anthropic-version": ANTHROPIC_VERSION,
                "Content-Type": "application/json",
            },
            "json": {
                "model": self.model,
                "max_tokens": settings.MAX_TOKENS,
                "temperature": 0.2,
                "system": system,
                "messages": [{"role": "user", "content": user}],
            },
        }

    def parse_response(self, data: Dict[str, Any]) -> tuple:
        text = data["content"][0]["text"]
        usage = data.get("usage") or {}
        tokens = None
        if "input_tokens" in usage or "output_tokens" in usage:
            tokens = int(usage.get("input_tokens", 0)) + int(usage.get("output_tokens", 0))
        return text, tokens
