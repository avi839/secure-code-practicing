"""
Built-in line-oriented rule engine for all supported languages.
"""

from typing import List

from app.services.scanner.findings import Finding, snippet, sort_findings
from app.services.scanner.rules import RULES, Rule

_HASH_COMMENT_LANGUAGES = {"python"}


def _is_comment(stripped: str, language: str) -> bool:
    if language in _HASH_COMMENT_LANGUAGES:
        return stripped.startswith("#")
    if language == "php" and stripped.startswith("#"):
        return True
    return stripped.startswith(("//", "/*", "*"))


class BuiltinScanner:
    """Regex rule engine. Deterministic: same input gives the same ordered output."""

    analyzer = "builtin"

    def __init__(self, rules: List[Rule] = None):
        self.rules = rules if rules is not None else RULES

    def _suppressed(self, rule: Rule, code: str) -> bool:
        return bool(rule.suppress_if_file_matches) and all(
            p.search(code) for p in rule.suppress_if_file_matches
        )

    def scan(self, code: str, language: str) -> List[Finding]:
        language = (language or "").lower()
        rules = [r for r in self.rules if r.applies_to(language) and not self._suppressed(r, code)]
        if not rules:
            return []

        findings: List[Finding] = []
        for line_no, line in enumerate(code.splitlines(), start=1):
            stripped = line.strip()
            if not stripped or _is_comment(stripped, language):
                continue
            for rule in rules:
                if not any(p.search(line) for p in rule.patterns):
                    continue
                if any(p.search(line) for p in rule.line_excludes):
                    continue
                findings.append(
                    Finding(
                        rule_id=rule.id,
                        analyzer=self.analyzer,
                        cwe_id=rule.cwe_id,
                        cwe_name=rule.cwe_name,
                        severity=rule.severity,
                        confidence=rule.confidence,
                        title=rule.title,
                        description=rule.why,
                        remediation=rule.fix,
                        start_line=line_no,
                        end_line=line_no,
                        code_snippet=snippet(line),
                    )
                )
        return sort_findings(findings)
