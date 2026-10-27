"""
Deterministic, per-rule code fixers.

Used only by the demo provider for user-supplied (non-curated) code. Each
fixer edits the finding's line in place and returns True if it changed
anything. SQL injection, path traversal and JS command injection have no
fixer: they need a real AI provider.
"""

import re
from typing import Callable, Dict, Iterable, List, Tuple

from app.services.scanner.findings import Finding
from app.services.scanner.rules import _SECRET_NAME

Fixer = Callable[[List[str], Finding], bool]

_IMPORT_RE = re.compile(r"^(?:import\s+\w|from\s+\S+\s+import\s)")


def ensure_import(lines: List[str], statement: str) -> bool:
    """Insert `statement` after the existing top-level imports. Returns True if inserted."""
    if any(line.strip() == statement for line in lines):
        return False
    last_import = -1
    for index, line in enumerate(lines):
        if _IMPORT_RE.match(line):
            last_import = index
    if last_import >= 0:
        lines.insert(last_import + 1, statement)
        return True
    insert_at = 0
    # Keep a shebang / encoding line at the top.
    while insert_at < len(lines) and lines[insert_at].startswith(("#!", "# -*-")):
        insert_at += 1
    lines.insert(insert_at, statement)
    return True


def _edit(lines: List[str], finding: Finding, transform: Callable[[str], str]) -> bool:
    index = finding.start_line - 1
    if not 0 <= index < len(lines):
        return False
    new_line = transform(lines[index])
    if new_line == lines[index]:
        return False
    lines[index] = new_line
    return True


# ----------------------------------------------------------------- Python fixers
def _fix_py_crypto(lines: List[str], finding: Finding) -> bool:
    def transform(line: str) -> str:
        line = re.sub(r"\bhashlib\.(?:md5|sha1)\(", "hashlib.sha256(", line)
        return re.sub(r"(\bhashlib\.new\(\s*)([\"'])(?:md5|sha1)\2", r"\1\2sha256\2", line)

    return _edit(lines, finding, transform)


_SUBPROCESS_STR_ARG = re.compile(
    r"(\bsubprocess\.(?:run|call|check_call|check_output|Popen)\(\s*)((?:f|rf|fr)?([\"'])[^\"']*\3)"
)


def _fix_py_cmdi(lines: List[str], finding: Finding) -> bool:
    needs_shlex = False
    needs_subprocess = False

    def transform(line: str) -> str:
        nonlocal needs_shlex, needs_subprocess
        new = line
        if re.search(r"\bshell\s*=\s*True\b", new):
            new = re.sub(r"\bshell\s*=\s*True\b", "shell=False", new)
            if _SUBPROCESS_STR_ARG.search(new):
                new = _SUBPROCESS_STR_ARG.sub(r"\1shlex.split(\2)", new, count=1)
                needs_shlex = True
        match = re.search(r"\bos\.system\((.*)\)\s*$", new)
        if match:
            new = new[: match.start()] + f"subprocess.run(shlex.split({match.group(1)}), check=True)"
            needs_shlex = needs_subprocess = True
        return new

    changed = _edit(lines, finding, transform)
    if changed:
        if needs_subprocess:
            ensure_import(lines, "import subprocess")
        if needs_shlex:
            ensure_import(lines, "import shlex")
    return changed


def _fix_py_deser(lines: List[str], finding: Finding) -> bool:
    needs_json = False

    def transform(line: str) -> str:
        nonlocal needs_json
        new = re.sub(r"\b(?:c?[Pp]ickle|dill)\.loads\(", "json.loads(", line)
        new = re.sub(r"\b(?:c?[Pp]ickle|dill)\.load\(", "json.load(", new)
        if new != line:
            needs_json = True
        new = re.sub(r"\byaml\.(?:unsafe_)?load\(", "yaml.safe_load(", new)
        new = re.sub(r",\s*Loader\s*=\s*[\w.]+", "", new) if "yaml.safe_load(" in new else new
        return new

    changed = _edit(lines, finding, transform)
    if changed and needs_json:
        ensure_import(lines, "import json")
    return changed


_PY_SECRET_ASSIGN = re.compile(rf"\b(\w*{_SECRET_NAME}\w*)(\s*=\s*)([\"'])[^\"']{{6,}}\3", re.I)


def _fix_py_secret(lines: List[str], finding: Finding) -> bool:
    def transform(line: str) -> str:
        return _PY_SECRET_ASSIGN.sub(
            lambda m: f'{m.group(1)}{m.group(2)}os.environ.get("{m.group(1).upper()}", "")', line, count=1
        )

    changed = _edit(lines, finding, transform)
    if changed:
        ensure_import(lines, "import os")
    return changed


def _fix_py_eval(lines: List[str], finding: Finding) -> bool:
    changed = _edit(lines, finding, lambda line: re.sub(r"(?<![.\w])eval\(", "ast.literal_eval(", line))
    if changed:
        ensure_import(lines, "import ast")
    return changed


# ------------------------------------------------------------- JavaScript fixers
def _fix_js_xss(lines: List[str], finding: Finding) -> bool:
    return _edit(lines, finding, lambda line: re.sub(r"\.innerHTML(\s*=)", r".textContent\1", line))


_JS_SECRET_DECL = re.compile(
    rf"\b((?:const|let|var)\s+)(\w*{_SECRET_NAME}\w*)(\s*=\s*)([\"'`])[^\"'`]{{6,}}\4", re.I
)
_JS_SECRET_KEY = re.compile(rf"\b(\w*{_SECRET_NAME}\w*)([\"']?\s*:\s*)([\"'`])[^\"'`]{{6,}}\3", re.I)


def _fix_js_secret(lines: List[str], finding: Finding) -> bool:
    def transform(line: str) -> str:
        new = _JS_SECRET_DECL.sub(
            lambda m: f"{m.group(1)}{m.group(2)}{m.group(3)}process.env.{m.group(2).upper()}", line, count=1
        )
        if new == line:
            new = _JS_SECRET_KEY.sub(
                lambda m: f"{m.group(1)}{m.group(2)}process.env.{m.group(1).upper()}", line, count=1
            )
        return new

    return _edit(lines, finding, transform)


def _fix_js_crypto(lines: List[str], finding: Finding) -> bool:
    return _edit(
        lines,
        finding,
        lambda line: re.sub(r"(\bcreateHash\(\s*)([\"'`])(?:md5|sha1)\2", r"\1\2sha256\2", line, flags=re.I),
    )


def _fix_js_eval(lines: List[str], finding: Finding) -> bool:
    return _edit(lines, finding, lambda line: re.sub(r"(?<![.\w])eval\(", "JSON.parse(", line))


FIXERS: Dict[str, Fixer] = {
    "PY-CRYPTO-001": _fix_py_crypto,
    "PY-CMDI-001": _fix_py_cmdi,
    "PY-DESER-001": _fix_py_deser,
    "PY-SECRET-001": _fix_py_secret,
    "PY-EVAL-001": _fix_py_eval,
    "JS-XSS-001": _fix_js_xss,
    "JS-SECRET-001": _fix_js_secret,
    "JS-CRYPTO-001": _fix_js_crypto,
    "JS-EVAL-001": _fix_js_eval,
}


def has_fixer(finding: Finding) -> bool:
    return finding.rule_id in FIXERS


def apply_fixes(code: str, findings: Iterable[Finding]) -> Tuple[str, List[str]]:
    """
    Apply fixers for the given findings. Returns (new_code, fixed_rule_ids).
    Findings are processed top to bottom; lines inserted by ensure_import shift
    the remaining findings accordingly.
    """
    lines = code.splitlines()
    trailing_newline = code.endswith("\n")
    fixed: List[str] = []
    shift = 0
    for finding in sorted(findings, key=lambda f: f.start_line):
        fixer = FIXERS.get(finding.rule_id)
        if fixer is None:
            continue
        shifted = Finding(**{**finding.to_dict(), "start_line": finding.start_line + shift,
                             "end_line": finding.end_line + shift})
        before = len(lines)
        if fixer(lines, shifted):
            fixed.append(finding.rule_id)
        shift += len(lines) - before
    new_code = "\n".join(lines) + ("\n" if trailing_newline else "")
    return new_code, fixed
