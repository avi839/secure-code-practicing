"""
Provider abstractions shared by the demo and HTTP (OpenAI/Anthropic/Gemini) providers.
"""

import asyncio
import logging
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class ProviderError(Exception):
    """A provider call failed. The message is sanitized and safe to show to users."""


class ProviderNotConfigured(ProviderError):
    """The provider has no API key configured."""


@dataclass
class ProviderResult:
    code: str
    raw_response: str
    prompt: str
    tokens_used: Optional[int] = None
    notes: Optional[str] = None
    model: Optional[str] = None


@dataclass
class RepairContext:
    task: str
    language: str
    previous_code: str
    previous_version: str
    findings: List[Any] = field(default_factory=list)
    round_number: int = 1


_FENCE_RE = re.compile(r"```[^\n`]*\n(.*?)```", re.DOTALL)


def extract_code(text: str) -> str:
    """Return the first fenced code block (any language tag) or the stripped text."""
    if not text:
        return ""
    match = _FENCE_RE.search(text)
    if match:
        return match.group(1).strip("\n")
    return text.strip()


class AIProvider(ABC):
    name: str = "base"
    label: str = "Base"
    model: str = ""
    is_demo: bool = False

    @abstractmethod
    async def generate_code(self, task: str, language: str) -> ProviderResult:
        ...

    @abstractmethod
    async def repair_code(self, prompt: str, ctx: RepairContext) -> ProviderResult:
        ...


RETRYABLE_STATUS = {429, 500, 502, 503, 504}
RETRY_DELAY_SECONDS = 2.0


class HTTPProvider(AIProvider):
    """Shared request/retry/sanitising logic for the HTTP providers."""

    def __init__(
        self,
        api_key: Optional[str],
        model: Optional[str] = None,
        transport: Optional[httpx.AsyncBaseTransport] = None,
        retry_delay: float = RETRY_DELAY_SECONDS,
    ):
        if not api_key:
            raise ProviderNotConfigured(f"{self.label} API key is not configured")
        self._api_key = api_key
        self.model = model or self.default_model()
        self._transport = transport
        self._retry_delay = retry_delay

    # Subclasses implement these -------------------------------------------------
    def default_model(self) -> str:  # pragma: no cover - overridden
        raise NotImplementedError

    def build_request(self, system: str, user: str) -> Dict[str, Any]:  # pragma: no cover
        """Return {"url", "headers", "json"}."""
        raise NotImplementedError

    def parse_response(self, data: Dict[str, Any]) -> tuple:  # pragma: no cover
        """Return (text, tokens_used)."""
        raise NotImplementedError

    # Shared ------------------------------------------------------------------------
    async def _complete(self, user_prompt: str) -> tuple:
        from app.services.prompts import SYSTEM_PROMPT

        request = self.build_request(SYSTEM_PROMPT, user_prompt)
        attempts = 2
        async with httpx.AsyncClient(timeout=settings.AI_TIMEOUT_SECONDS, transport=self._transport) as client:
            for attempt in range(1, attempts + 1):
                started = time.perf_counter()
                try:
                    response = await client.post(request["url"], headers=request["headers"], json=request["json"])
                except httpx.TimeoutException:
                    logger.warning("provider=%s model=%s status=timeout", self.name, self.model)
                    if attempt < attempts:
                        await asyncio.sleep(self._retry_delay)
                        continue
                    raise ProviderError(f"{self.label} request failed (timeout)") from None
                except httpx.HTTPError:
                    logger.warning("provider=%s model=%s status=network_error", self.name, self.model)
                    raise ProviderError(f"{self.label} request failed (network error)") from None

                latency_ms = int((time.perf_counter() - started) * 1000)
                logger.info(
                    "provider=%s model=%s status_code=%s latency_ms=%s",
                    self.name, self.model, response.status_code, latency_ms,
                )
                if response.status_code in RETRYABLE_STATUS and attempt < attempts:
                    await asyncio.sleep(self._retry_delay)
                    continue
                if response.status_code >= 400:
                    raise ProviderError(f"{self.label} request failed (HTTP {response.status_code})")
                try:
                    text, tokens = self.parse_response(response.json())
                except Exception:
                    raise ProviderError(f"{self.label} returned an unexpected response") from None
                return text or "", tokens
        raise ProviderError(f"{self.label} request failed")  # pragma: no cover

    async def generate_code(self, task: str, language: str) -> ProviderResult:
        from app.services.prompts import build_generation_prompt

        prompt = build_generation_prompt(task, language)
        text, tokens = await self._complete(prompt)
        return ProviderResult(code=extract_code(text), raw_response=text, prompt=prompt,
                              tokens_used=tokens, model=self.model)

    async def repair_code(self, prompt: str, ctx: RepairContext) -> ProviderResult:
        text, tokens = await self._complete(prompt)
        return ProviderResult(code=extract_code(text), raw_response=text, prompt=prompt,
                              tokens_used=tokens, model=self.model)
