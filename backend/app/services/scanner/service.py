"""
ScannerService: runs the built-in engine (all languages) and Bandit (Python),
merges and de-duplicates the results and computes the security label.
"""

import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from app.services.scanner.bandit_runner import BanditScanner
from app.services.scanner.builtin import BuiltinScanner
from app.services.scanner.findings import SEVERITIES, Finding, security_label, sort_findings

# Bandit and the built-in rules use different but equivalent CWE ids for some issues.
CWE_EQUIVALENCE = {"CWE-259": "CWE-798", "CWE-94": "CWE-95"}


def normalize_cwe(cwe_id: Optional[str]) -> Optional[str]:
    return CWE_EQUIVALENCE.get(cwe_id, cwe_id)


@dataclass
class ScanReport:
    findings: List[Finding]
    label: int  # 1 = insecure (any MEDIUM+ finding), 0 = secure
    severity_counts: Dict[str, int]
    analyzers_run: List[str]
    errors: List[str] = field(default_factory=list)

    @property
    def is_secure(self) -> bool:
        return self.label == 0

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "is_secure": self.is_secure,
            "findings": [f.to_dict() for f in self.findings],
            "severity_counts": dict(self.severity_counts),
            "analyzers_run": list(self.analyzers_run),
            "errors": list(self.errors),
        }


def count_severities(findings: List[Finding]) -> Dict[str, int]:
    counts = {severity: 0 for severity in SEVERITIES}
    for finding in findings:
        if finding.severity in counts:
            counts[finding.severity] += 1
    return counts


def merge_findings(builtin: List[Finding], bandit: List[Finding]) -> List[Finding]:
    """Fold Bandit findings into equivalent built-in findings (same line + same CWE)."""
    merged = list(builtin)
    for extra in bandit:
        match = next(
            (
                f
                for f in merged
                if f.analyzer == "builtin"
                and f.start_line == extra.start_line
                and normalize_cwe(f.cwe_id) == normalize_cwe(extra.cwe_id)
            ),
            None,
        )
        if match is not None:
            tag = f"bandit:{extra.rule_id.replace('BANDIT-', '')}"
            if tag not in match.corroborated_by:
                match.corroborated_by.append(tag)
        else:
            merged.append(extra)
    return sort_findings(merged)


class ScannerService:
    def __init__(self, builtin: Optional[BuiltinScanner] = None, bandit: Optional[BanditScanner] = None):
        self.builtin = builtin or BuiltinScanner()
        self.bandit = bandit or BanditScanner()

    def scan(self, code: str, language: str) -> ScanReport:
        language = (language or "").lower()
        analyzers = ["builtin"]
        errors: List[str] = []
        findings = self.builtin.scan(code, language)

        if language == "python" and self.bandit.enabled():
            analyzers.append("bandit")
            bandit_findings, error = self.bandit.scan(code)
            if error:
                errors.append(error)
            findings = merge_findings(findings, bandit_findings)

        return ScanReport(
            findings=findings,
            label=security_label(findings),
            severity_counts=count_severities(findings),
            analyzers_run=analyzers,
            errors=errors,
        )

    async def scan_async(self, code: str, language: str) -> ScanReport:
        """Run the (subprocess-based) scan in a worker thread so the event loop is not blocked."""
        return await asyncio.to_thread(self.scan, code, language)
