"""Google Gemini generateContent provider (plain httpx). The key is sent only in a header."""

from typing import Any, Dict
from urllib.parse import quote

from app.config import settings
from app.services.providers.base import HTTPProvider

GEMINI_URL_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class GeminiProvider(HTTPProvider):
    name = "google"
    label = "Gemini"

    def default_model(self) -> str:
        return settings.GEMINI_MODEL

    def build_request(self, system: str, user: str) -> Dict[str, Any]:
        return {
            # Never put the key in the URL (it would end up in logs and proxies).
            "url": GEMINI_URL_TEMPLATE.format(model=quote(self.model, safe="-._")),
            "headers": {"x-goog-api-key": self._api_key, "Content-Type": "application/json"},
            "json": {
                "systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": user}]}],
                "generationConfig": {"temperature": 0.2, "maxOutputTokens": settings.MAX_TOKENS},
            },
        }

    def parse_response(self, data: Dict[str, Any]) -> tuple:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        tokens = (data.get("usageMetadata") or {}).get("totalTokenCount")
        return text, tokens
