"""
Reflexion engine (pure: no database access).

t0 = user code or provider.generate_code(task); each round k feeds the
previous version plus its static-analysis findings back to the provider
(see prompts.build_reflection_prompt), rescans the revision and records a
diff, a finding comparison and a deterministic explanation.
"""

import difflib
import time
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Dict, List, Optional

from app.services.metrics_service import compare_findings
from app.services.prompts import build_reflection_prompt
from app.services.providers.base import AIProvider, ProviderError, RepairContext, extract_code
from app.services.scanner import ScannerService, ScanReport

USER_CODE_PROMPT = "User-supplied code (no generation prompt was sent)."
SAME_CODE_EXPLANATION = "The model returned the same code; no changes were made."


@dataclass
class RoundResult:
    round_number: int
    version: str
    code: str
    raw_response: str
    prompt: str
    report: ScanReport
    diff: str
    comparison: Dict[str, List[dict]]
    explanation: str
    generation_time_seconds: float
    tokens_used: Optional[int] = None
    notes: Optional[str] = None
    findings_count: int = field(init=False)

    def __post_init__(self):
        self.findings_count = len(self.report.findings)


OnRound = Callable[[RoundResult], Awaitable[Optional[bool]]]


def unified_diff(prev_code: str, code: str, from_version: str, to_version: str) -> str:
    return "\n".join(
        difflib.unified_diff(
            prev_code.splitlines(), code.splitlines(), fromfile=from_version, tofile=to_version, lineterm=""
        )
    )


def diff_stats(diff: str) -> tuple:
    added = sum(1 for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++"))
    removed = sum(1 for line in diff.splitlines() if line.startswith("-") and not line.startswith("---"))
    return added, removed


def _describe(item: dict) -> str:
    return f"{item.get('cwe_id')} {item.get('title')}"


def build_explanation(previous: "RoundResult", report: ScanReport, comparison: Dict[str, List[dict]],
                      diff: str, notes: Optional[str], unchanged: bool) -> str:
    if unchanged:
        return SAME_CODE_EXPLANATION + (f" {notes}" if notes else "")

    remediation_by_rule = {f.rule_id: f.remediation for f in previous.report.findings}
    parts = []
    fixed = comparison.get("fixed", [])
    new = comparison.get("new", [])
    unresolved = comparison.get("unresolved", [])
    if fixed:
        described = []
        for item in fixed:
            remediation = (remediation_by_rule.get(item.get("rule_id")) or "").strip().rstrip(".")
            described.append(f"{_describe(item)} \u2013 {remediation}" if remediation else _describe(item))
        items = "; ".join(described)
        parts.append(f"Fixed {len(fixed)} issue(s): {items}.")
    if new:
        lines_by_rule = {}
        for finding in report.findings:
            lines_by_rule.setdefault(finding.rule_id, finding.start_line)
        items = "; ".join(f"{_describe(item)} (line {lines_by_rule.get(item.get('rule_id'), '?')})" for item in new)
        parts.append(f"Introduced {len(new)} new issue(s): {items}.")
    if unresolved:
        items = ", ".join(sorted({_describe(item) for item in unresolved}))
        parts.append(f"{len(unresolved)} issue(s) remain: {items}.")
    if not (fixed or new or unresolved):
        parts.append("No security findings before or after this revision.")
    if notes:
        parts.append(notes.rstrip(".") + ".")
    added, removed = diff_stats(diff)
    parts.append(f"+{added}/\u2212{removed} lines changed.")
    return " ".join(parts)


def baseline_explanation(report: ScanReport, source: str, notes: Optional[str]) -> str:
    origin = "User-supplied baseline" if source == "user_code" else "Generated baseline"
    if report.findings:
        items = ", ".join(f"{f.cwe_id} {f.cwe_name} (line {f.start_line})" for f in report.findings)
        text = f"{origin} (t0): {len(report.findings)} issue(s) found: {items}."
    else:
        text = f"{origin} (t0): no security findings."
    return text + (f" {notes}" if notes else "")


class ReflexionEngine:
    def __init__(self, provider: AIProvider, scanner: ScannerService):
        self.provider = provider
        self.scanner = scanner
        self.stopped_early = False

    async def baseline(self, task: str, language: str, user_code: Optional[str]) -> RoundResult:
        started = time.perf_counter()
        if user_code is not None and user_code.strip():
            code, raw, prompt, tokens, notes, source = user_code, user_code, USER_CODE_PROMPT, None, None, "user_code"
        else:
            result = await self.provider.generate_code(task, language)
            code = result.code or extract_code(result.raw_response)
            if not code.strip():
                raise ProviderError(f"{self.provider.label} returned no code")
            raw, prompt, tokens, notes, source = result.raw_response, result.prompt, result.tokens_used, result.notes, "generated"
        elapsed = round(time.perf_counter() - started, 3)

        report = await self.scanner.scan_async(code, language)
        return RoundResult(
            round_number=0,
            version="t0",
            code=code,
            raw_response=raw,
            prompt=prompt,
            report=report,
            diff="",
            comparison={"fixed": [], "new": [], "unresolved": []},
            explanation=baseline_explanation(report, source, notes),
            generation_time_seconds=elapsed,
            tokens_used=tokens,
            notes=notes,
        )

    async def reflect(self, task: str, language: str, previous: RoundResult) -> RoundResult:
        round_number = previous.round_number + 1
        version = f"t{round_number}"
        prompt = build_reflection_prompt(task, language, previous.version, previous.code, previous.report.findings)
        ctx = RepairContext(
            task=task,
            language=language,
            previous_code=previous.code,
            previous_version=previous.version,
            findings=list(previous.report.findings),
            round_number=round_number,
        )

        started = time.perf_counter()
        result = await self.provider.repair_code(prompt, ctx)
        elapsed = round(time.perf_counter() - started, 3)

        code = result.code or extract_code(result.raw_response)
        if not code.strip():
            raise ProviderError(f"{self.provider.label} returned no code")

        report = await self.scanner.scan_async(code, language)
        diff = unified_diff(previous.code, code, previous.version, version)
        comparison = compare_findings(previous.report.findings, report.findings)
        unchanged = code.strip() == previous.code.strip()
        explanation = build_explanation(previous, report, comparison, diff, result.notes, unchanged)

        return RoundResult(
            round_number=round_number,
            version=version,
            code=code,
            raw_response=result.raw_response,
            prompt=prompt,
            report=report,
            diff=diff,
            comparison=comparison,
            explanation=explanation,
            generation_time_seconds=elapsed,
            tokens_used=result.tokens_used,
            notes=result.notes,
        )

    async def run(self, task: str, language: str, user_code: Optional[str], rounds: int,
                  on_round: Optional[OnRound] = None) -> List[RoundResult]:
        """
        Baseline plus up to `rounds` reflexion rounds. Stops early (stopped_early)
        once a version has zero findings, or when a version is labelled secure and
        the provider returned the previous code unchanged. `on_round` is awaited
        after every version; returning False from it stops the loop (e.g. the
        evaluation was cancelled).
        """
        self.stopped_early = False
        results = [await self.baseline(task, language, user_code)]
        if on_round is not None and await on_round(results[0]) is False:
            return results

        for _ in range(rounds):
            previous = results[-1]
            if not previous.report.findings:
                self.stopped_early = True
                break
            current = await self.reflect(task, language, previous)
            results.append(current)
            if on_round is not None and await on_round(current) is False:
                break
            # Secure (only LOW findings left) and the provider made no change: further rounds cannot help.
            if current.report.label == 0 and current.code.strip() == previous.code.strip():
                self.stopped_early = True
                break
        return results
