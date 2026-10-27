"""
Bandit integration (Python only). Runs `python -m bandit -f json` on a
temporary file that is always deleted afterwards.
"""

import importlib.util
import json
import logging
import os
import subprocess
import sys
import tempfile
from typing import List, Optional, Tuple

from app.config import settings
from app.services.scanner.findings import Finding, snippet, sort_findings

logger = logging.getLogger(__name__)

# B101 (assert) and B404 (import subprocess) are skipped: informational only.
SKIPPED_TESTS = "B101,B404"

_SEVERITY = {"HIGH": "HIGH", "MEDIUM": "MEDIUM", "LOW": "LOW", "UNDEFINED": "LOW"}

CWE_NAMES = {
    "CWE-22": "Path Traversal",
    "CWE-78": "OS Command Injection",
    "CWE-79": "Cross-site Scripting (XSS)",
    "CWE-89": "SQL Injection",
    "CWE-94": "Code Injection",
    "CWE-95": "Eval Injection",
    "CWE-259": "Use of Hard-coded Password",
    "CWE-295": "Improper Certificate Validation",
    "CWE-327": "Use of a Broken or Risky Cryptographic Algorithm",
    "CWE-330": "Use of Insufficiently Random Values",
    "CWE-377": "Insecure Temporary File",
    "CWE-400": "Uncontrolled Resource Consumption",
    "CWE-502": "Deserialization of Untrusted Data",
    "CWE-605": "Multiple Binds to the Same Port",
    "CWE-703": "Improper Check or Handling of Exceptional Conditions",
    "CWE-798": "Use of Hard-coded Credentials",
}

BANDIT_FIX = {
    "B105": "Load the password from the environment or a secrets manager instead of a string literal.",
    "B106": "Pass credentials from configuration or the environment, not as literal arguments.",
    "B107": "Do not use hard-coded default passwords; require the value from configuration.",
    "B301": "Use json.loads() (or another data-only format) for untrusted data instead of pickle.",
    "B302": "Use json instead of marshal for untrusted data.",
    "B303": "Use SHA-256 or stronger; for passwords use a salted KDF such as pbkdf2_hmac.",
    "B307": "Use ast.literal_eval() for literals or an explicit allow-list instead of eval().",
    "B324": "Use hashlib.sha256() or stronger; for passwords use hashlib.pbkdf2_hmac/scrypt.",
    "B506": "Use yaml.safe_load() instead of yaml.load().",
    "B602": "Pass an argument list to subprocess with shell=False and validate the input.",
    "B605": "Replace os.system()/os.popen() with subprocess.run([...], shell=False).",
    "B608": "Use a parameterized query with placeholders instead of building SQL strings.",
}


# Bandit reports eval() (B307) as CWE-78; eval injection is CWE-95, which lets it merge
# with the built-in PY-EVAL-001 finding instead of being shown twice.
BANDIT_CWE_OVERRIDE = {"B307": "CWE-95"}


def bandit_available() -> bool:
    return importlib.util.find_spec("bandit") is not None


class BanditScanner:
    analyzer = "bandit"

    def enabled(self) -> bool:
        return settings.BANDIT_ENABLED and bandit_available()

    def scan(self, code: str) -> Tuple[List[Finding], Optional[str]]:
        """Return (findings, error_message). Never raises."""
        path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False, encoding="utf-8"
            ) as handle:
                handle.write(code)
                path = handle.name
            proc = subprocess.run(  # noqa: S603 - fixed argument list, no shell
                [sys.executable, "-m", "bandit", "-f", "json", "-q", "-s", SKIPPED_TESTS, path],
                capture_output=True,
                text=True,
                timeout=settings.SCANNER_TIMEOUT_SECONDS,
                shell=False,
            )
            data = json.loads(proc.stdout or "{}")
            lines = code.splitlines()
            findings = [self._to_finding(item, lines) for item in data.get("results", [])]
            return sort_findings(findings), None
        except subprocess.TimeoutExpired:
            logger.warning("bandit scan timed out")
            return [], "bandit timed out"
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("bandit scan failed: %s", type(exc).__name__)
            return [], "bandit failed to run"
        finally:
            if path:
                try:
                    os.unlink(path)
                except OSError:
                    pass

    def _to_finding(self, item: dict, lines: List[str]) -> Finding:
        test_id = item.get("test_id", "B000")
        cwe = item.get("issue_cwe") or {}
        cwe_id = BANDIT_CWE_OVERRIDE.get(test_id) or (f"CWE-{cwe['id']}" if cwe.get("id") else "CWE-710")
        line_no = int(item.get("line_number") or 1)
        line_range = item.get("line_range") or [line_no]
        source_line = lines[line_no - 1] if 0 < line_no <= len(lines) else ""
        remediation = BANDIT_FIX.get(test_id) or f"See Bandit docs: {item.get('more_info', '')}".strip()
        return Finding(
            rule_id=f"BANDIT-{test_id}",
            analyzer=self.analyzer,
            cwe_id=cwe_id,
            cwe_name=CWE_NAMES.get(cwe_id, item.get("test_name", "Security weakness")),
            severity=_SEVERITY.get(str(item.get("issue_severity", "LOW")).upper(), "LOW"),
            confidence=_SEVERITY.get(str(item.get("issue_confidence", "LOW")).upper(), "LOW"),
            title=str(item.get("test_name", test_id)).replace("_", " ").capitalize(),
            description=str(item.get("issue_text", "")).strip(),
            remediation=remediation,
            start_line=line_no,
            end_line=int(max(line_range)) if line_range else line_no,
            code_snippet=snippet(source_line),
        )
