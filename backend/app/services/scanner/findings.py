"""
Normalised security finding model and severity helpers.
"""

from dataclasses import asdict, dataclass, field
from typing import Dict, Iterable, List

SEVERITY_ORDER: Dict[str, int] = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
SEVERITIES: List[str] = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]

# D10: a version is insecure if any finding is MEDIUM or worse.
INSECURE_THRESHOLD = SEVERITY_ORDER["MEDIUM"]


@dataclass
class Finding:
    rule_id: str
    analyzer: str  # "builtin" | "bandit"
    cwe_id: str  # e.g. "CWE-89"
    cwe_name: str
    severity: str  # CRITICAL | HIGH | MEDIUM | LOW
    confidence: str  # HIGH | MEDIUM | LOW
    title: str
    description: str  # why it is vulnerable
    remediation: str  # how to fix it
    start_line: int
    end_line: int
    code_snippet: str
    corroborated_by: List[str] = field(default_factory=list)

    @property
    def severity_rank(self) -> int:
        return SEVERITY_ORDER.get(self.severity, 0)

    def to_dict(self) -> dict:
        return asdict(self)


def severity_rank(severity: str) -> int:
    return SEVERITY_ORDER.get((severity or "").upper(), 0)


def is_insecure(findings: Iterable[Finding]) -> bool:
    """True if any finding is CRITICAL, HIGH or MEDIUM (LOW does not flip the label)."""
    return any(severity_rank(f.severity) >= INSECURE_THRESHOLD for f in findings)


def security_label(findings: Iterable[Finding]) -> int:
    """Binary label: 1 = insecure, 0 = secure."""
    return 1 if is_insecure(findings) else 0


def snippet(line: str, limit: int = 200) -> str:
    text = line.strip()
    return text if len(text) <= limit else text[: limit - 1] + "\u2026"


def sort_findings(findings: Iterable[Finding]) -> List[Finding]:
    return sorted(findings, key=lambda f: (f.start_line, -f.severity_rank, f.rule_id))
