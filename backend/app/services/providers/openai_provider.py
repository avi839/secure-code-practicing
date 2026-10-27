"""OpenAI Chat Completions provider (plain httpx)."""

from typing import Any, Dict

from app.config import settings
from app.services.providers.base import HTTPProvider

OPENAI_URL = "https://api.openai.com/v1/chat/completions"


class OpenAIProvider(HTTPProvider):
    name = "openai"
    label = "OpenAI"

    def default_model(self) -> str:
        return settings.OPENAI_MODEL

    def build_request(self, system: str, user: str) -> Dict[str, Any]:
        return {
            "url": OPENAI_URL,
            "headers": {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
            "json": {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.2,
                "max_tokens": settings.MAX_TOKENS,
            },
        }

    def parse_response(self, data: Dict[str, Any]) -> tuple:
        text = data["choices"][0]["message"]["content"]
        tokens = (data.get("usage") or {}).get("total_tokens")
        return text, tokens
