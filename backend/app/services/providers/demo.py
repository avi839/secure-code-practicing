"""
Demo provider: works without API keys.

- generate_code returns stage 0 of the curated sample that best matches the task.
- repair_code advances curated samples to their next stage; for any other code it
  applies deterministic autofixes one severity tier per round (progressive repair).
"""

import asyncio
from typing import List

from app.config import settings
from app.services.autofix import apply_fixes, has_fixer
from app.services.prompts import build_generation_prompt
from app.services.providers.base import AIProvider, ProviderError, ProviderResult, RepairContext
from app.services.providers.demo_samples import find_stage, select_sample
from app.services.scanner.findings import SEVERITIES

DEMO_MODEL = "securereflex-demo-1"


def _fence(code: str, language: str) -> str:
    return f"```{language}\n{code.rstrip()}\n```"


def _estimate_tokens(*texts: str) -> int:
    """Rough estimate (~4 characters per token); labelled as an estimate in the UI."""
    return sum(len(t or "") for t in texts) // 4


class DemoProvider(AIProvider):
    name = "demo"
    label = "Demo"
    is_demo = True

    def __init__(self, model: str = None):
        self.model = model or DEMO_MODEL

    async def _latency(self) -> None:
        if settings.DEMO_LATENCY_MS > 0:
            await asyncio.sleep(settings.DEMO_LATENCY_MS / 1000)

    async def generate_code(self, task: str, language: str) -> ProviderResult:
        await self._latency()
        sample = select_sample(language, task)
        if sample is None:
            raise ProviderError(f"Demo provider has no sample for language '{language}'")
        prompt = build_generation_prompt(task, language)
        code = sample.stages[0]
        return ProviderResult(
            code=code,
            raw_response=_fence(code, language),
            prompt=prompt,
            tokens_used=_estimate_tokens(prompt, code),
            notes=f"Demo sample '{sample.id}': {sample.stage_notes[0]}" if sample.stage_notes else None,
            model=self.model,
        )

    async def repair_code(self, prompt: str, ctx: RepairContext) -> ProviderResult:
        await self._latency()
        match = find_stage(ctx.previous_code)
        if match is not None:
            sample, index = match
            next_index = min(index + 1, len(sample.stages) - 1)
            code = sample.stages[next_index]
            if next_index == index:
                notes = "The curated sample is already at its final repaired stage; no further changes."
            else:
                notes = sample.stage_notes[next_index] if next_index < len(sample.stage_notes) else None
            return self._result(code, prompt, ctx.language, notes)

        return self._autofix(prompt, ctx)

    def _autofix(self, prompt: str, ctx: RepairContext) -> ProviderResult:
        findings = list(ctx.findings or [])
        unfixable = sorted({f.rule_id for f in findings if not has_fixer(f)})

        tier: List = []
        for severity in SEVERITIES:
            tier = [f for f in findings if f.severity == severity and has_fixer(f)]
            if tier:
                break

        if not tier:
            notes = (
                f"Demo provider cannot auto-repair {', '.join(unfixable)}; configure a real AI provider."
                if unfixable
                else "No findings to repair."
            )
            return self._result(ctx.previous_code, prompt, ctx.language, notes)

        code, fixed = apply_fixes(ctx.previous_code, tier)
        parts = []
        if fixed:
            parts.append(
                f"Applied deterministic {tier[0].severity} fixes for {', '.join(sorted(set(fixed)))}."
            )
        if unfixable:
            parts.append(
                f"Demo provider cannot auto-repair {', '.join(unfixable)}; configure a real AI provider."
            )
        return self._result(code, prompt, ctx.language, " ".join(parts) or None)

    def _result(self, code: str, prompt: str, language: str, notes) -> ProviderResult:
        return ProviderResult(
            code=code,
            raw_response=_fence(code, language),
            prompt=prompt,
            tokens_used=_estimate_tokens(prompt, code),
            notes=notes,
            model=self.model,
        )
