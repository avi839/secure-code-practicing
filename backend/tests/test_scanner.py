import os
import subprocess
import tempfile

import pytest

from app.services.autofix import apply_fixes, ensure_import
from app.services.scanner import ScannerService
from app.services.scanner.bandit_runner import BanditScanner, bandit_available
from app.services.scanner.builtin import BuiltinScanner
from app.services.scanner.findings import Finding, is_insecure
from app.services.scanner.rules import RULES
from app.services.scanner.service import merge_findings

builtin = BuiltinScanner()

# (rule_id, language, positive line, negative line)
RULE_CASES = [
    ("PY-SQLI-001", "python", "q = f\"SELECT * FROM users WHERE name = '{name}'\"",
     'cur.execute("SELECT * FROM users WHERE name = ?", (name,))'),
    ("PY-SQLI-001", "python", 'q = "SELECT * FROM users WHERE id = %s" % uid',
     'q = "SELECT * FROM users WHERE id = %s"'),
    ("PY-CMDI-001", "python", "subprocess.run(cmd, shell=True)", 'subprocess.run(["ls", path])'),
    ("PY-CMDI-001", "python", "os.system(cmd)", "os.getcwd()"),
    ("PY-PATH-001", "python", "with open(filename) as f:", 'with open("config.ini") as f:'),
    ("PY-DESER-001", "python", "data = pickle.loads(blob)", "data = json.loads(blob)"),
    ("PY-DESER-001", "python", "cfg = yaml.load(text)", "cfg = yaml.load(text, Loader=yaml.SafeLoader)"),
    ("PY-CRYPTO-001", "python", "h = hashlib.md5(data)", "h = hashlib.sha256(data)"),
    ("PY-SECRET-001", "python", 'API_KEY = "abcdef123456"', 'API_KEY = os.environ["API_KEY"]'),
    ("PY-EVAL-001", "python", "result = eval(expr)", "result = ast.literal_eval(expr)"),
    ("PY-XSS-001", "python", "return render_template_string(template)",
     'return render_template_string("<p>hi</p>")'),
    ("JS-XSS-001", "javascript", "el.innerHTML = userInput;", "el.textContent = userInput;"),
    ("JS-XSS-001", "javascript", 'res.send("<h1>" + req.query.name + "</h1>");',
     'res.send("<h1>" + escapeHtml(req.query.name) + "</h1>");'),
    ("JS-SQLI-001", "javascript", 'const q = "SELECT * FROM users WHERE id = " + id;',
     'const q = "SELECT * FROM users WHERE id = ?";'),
    ("JS-CMDI-001", "javascript", "exec(`ls ${dir}`, cb);", 'execFile("ls", [dir], cb);'),
    ("JS-PATH-001", "javascript", "fs.readFile(req.query.file, cb);", 'fs.readFile("config.json", cb);'),
    ("JS-SECRET-001", "javascript", 'const apiKey = "sk-123456789";', "const apiKey = process.env.API_KEY;"),
    ("JS-CRYPTO-001", "javascript", 'crypto.createHash("md5")', 'crypto.createHash("sha256")'),
    ("JS-EVAL-001", "javascript", "eval(code);", "JSON.parse(code);"),
    ("JS-DESER-001", "javascript", "const obj = serialize.unserialize(data);", "const obj = JSON.parse(data);"),
    ("GEN-SECRET-001", "java", 'String password = "hunter22";',
     'String password = System.getenv("DB_PASSWORD");'),
    ("GEN-SECRET-001", "csharp", '"Server=db;User Id=app;Password=Winter2024!;"',
     'Environment.GetEnvironmentVariable("DB_CONNECTION")'),
    ("GEN-CRYPTO-001", "java", 'MessageDigest.getInstance("MD5");', 'MessageDigest.getInstance("SHA-256");'),
    ("GEN-SQLI-001", "java", 'String q = "SELECT * FROM users WHERE id = " + id;',
     'conn.prepareStatement("SELECT * FROM users WHERE id = ?");'),
    ("GEN-SQLI-001", "php", '$r = mysqli_query($db, "SELECT * FROM t WHERE id = " . $id);',
     '$stmt = $db->prepare("SELECT * FROM t WHERE id = ?");'),
    ("C-BOF-001", "c", "strcpy(dst, src);", "strncpy(dst, src, sizeof(dst) - 1);"),
    ("C-CMDI-001", "c", "system(cmd);", 'system("ls -l");'),
    ("JAVA-CMDI-001", "java", 'Runtime.getRuntime().exec("ping " + host);',
     'new ProcessBuilder("ping", host).start();'),
    ("PHP-CMDI-001", "php", "$out = shell_exec($cmd);", '$out = shell_exec("ls");'),
    ("PHP-XSS-001", "php", 'echo $_GET["name"];', 'echo htmlspecialchars($_GET["name"], ENT_QUOTES, "UTF-8");'),
]


def _rule_ids(code, language):
    return [f.rule_id for f in builtin.scan(code, language)]


@pytest.mark.parametrize("rule_id,language,positive,negative", RULE_CASES)
def test_rule_positive_and_negative(rule_id, language, positive, negative):
    assert rule_id in _rule_ids(positive, language)
    assert rule_id not in _rule_ids(negative, language)


def test_every_rule_has_a_case():
    covered = {case[0] for case in RULE_CASES}
    assert {rule.id for rule in RULES} <= covered


def test_finding_fields_and_line_numbers():
    code = "import sqlite3\n\n\ndef f(c, name):\n    return c.execute(f\"SELECT * FROM u WHERE n = '{name}'\")\n"
    findings = builtin.scan(code, "python")
    assert len(findings) == 1
    f = findings[0]
    assert (f.start_line, f.end_line) == (5, 5)
    assert f.cwe_id == "CWE-89" and f.severity == "CRITICAL" and f.analyzer == "builtin"
    assert f.description and f.remediation and f.code_snippet.startswith("return c.execute")
    assert f.to_dict()["rule_id"] == "PY-SQLI-001"


def test_comments_are_skipped():
    assert _rule_ids("# os.system(cmd)\n", "python") == []
    assert _rule_ids("// eval(code);\n", "javascript") == []


def test_path_rule_suppressed_by_containment_check():
    code = (
        "import os\n"
        "def read(name):\n"
        "    p = os.path.realpath(os.path.join(BASE, name))\n"
        "    if os.path.commonpath([BASE, p]) != BASE:\n"
        "        raise ValueError\n"
        "    return open(p).read()\n"
    )
    assert "PY-PATH-001" not in _rule_ids(code, "python")


def test_deterministic_order():
    code = 'API_KEY = "abcdef123456"\nh = hashlib.md5(x)\nos.system(cmd)\nr = eval(s)\n'
    first = [(f.start_line, f.rule_id) for f in builtin.scan(code, "python")]
    second = [(f.start_line, f.rule_id) for f in builtin.scan(code, "python")]
    assert first == second == sorted(first)


def _finding(rule_id, cwe, line, severity="HIGH", analyzer="builtin"):
    return Finding(rule_id=rule_id, analyzer=analyzer, cwe_id=cwe, cwe_name="x", severity=severity,
                   confidence="HIGH", title="t", description="d", remediation="r",
                   start_line=line, end_line=line, code_snippet="s")


def test_merge_dedupes_with_cwe_equivalence():
    builtin_findings = [_finding("PY-SECRET-001", "CWE-798", 3)]
    bandit_findings = [
        _finding("BANDIT-B105", "CWE-259", 3, "LOW", "bandit"),
        _finding("BANDIT-B403", "CWE-502", 1, "LOW", "bandit"),
    ]
    merged = merge_findings(builtin_findings, bandit_findings)
    assert [f.rule_id for f in merged] == ["BANDIT-B403", "PY-SECRET-001"]
    assert merged[1].corroborated_by == ["bandit:B105"]


def test_low_findings_do_not_flip_label():
    assert not is_insecure([_finding("BANDIT-B603", "CWE-78", 1, "LOW", "bandit")])
    assert is_insecure([_finding("X", "CWE-1", 1, "MEDIUM")])


def test_unknown_language_returns_nothing():
    assert ScannerService().scan("eval(x)", "cobol").findings == []


bandit_only = pytest.mark.skipif(not bandit_available(), reason="bandit is not importable")


@bandit_only
def test_bandit_corroborates_builtin_finding():
    code = "import sqlite3\n\ndef f(c, name):\n    return c.execute(f\"SELECT * FROM u WHERE n = '{name}'\")\n"
    report = ScannerService().scan(code, "python")
    assert report.analyzers_run == ["builtin", "bandit"]
    sqli = [f for f in report.findings if f.cwe_id == "CWE-89"]
    assert len(sqli) == 1 and sqli[0].analyzer == "builtin"
    assert "bandit:B608" in sqli[0].corroborated_by
    assert report.label == 1 and report.severity_counts["CRITICAL"] == 1


@bandit_only
def test_bandit_temp_file_removed(monkeypatch):
    created = []
    original = tempfile.NamedTemporaryFile

    def tracking(*args, **kwargs):
        handle = original(*args, **kwargs)
        created.append(handle.name)
        return handle

    monkeypatch.setattr(tempfile, "NamedTemporaryFile", tracking)
    findings, error = BanditScanner().scan("import pickle\npickle.loads(b'')\n")
    assert error is None and any(f.rule_id == "BANDIT-B301" for f in findings)
    assert created and not any(os.path.exists(p) for p in created)


def test_bandit_timeout_is_reported_not_raised(monkeypatch):
    created = []
    original = tempfile.NamedTemporaryFile

    def tracking(*args, **kwargs):
        handle = original(*args, **kwargs)
        created.append(handle.name)
        return handle

    def boom(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="bandit", timeout=1)

    monkeypatch.setattr(tempfile, "NamedTemporaryFile", tracking)
    monkeypatch.setattr(subprocess, "run", boom)
    findings, error = BanditScanner().scan("x = 1\n")
    assert findings == [] and error == "bandit timed out"
    assert created and not os.path.exists(created[0])


# ------------------------------------------------------------------ autofix
def test_autofix_crypto_and_eval():
    code = "import hashlib\nh = hashlib.md5(b)\nv = eval(s)\n"
    findings = builtin.scan(code, "python")
    fixed_code, fixed = apply_fixes(code, findings)
    assert "hashlib.sha256(" in fixed_code and "ast.literal_eval(" in fixed_code
    assert "import ast" in fixed_code
    assert sorted(fixed) == ["PY-CRYPTO-001", "PY-EVAL-001"]
    assert builtin.scan(fixed_code, "python") == []


def test_autofix_js_xss_and_secret():
    code = 'const apiKey = "sk-123456789";\nel.innerHTML = comment;\n'
    fixed_code, fixed = apply_fixes(code, builtin.scan(code, "javascript"))
    assert "process.env.APIKEY" in fixed_code and ".textContent =" in fixed_code
    assert builtin.scan(fixed_code, "javascript") == []


def test_autofix_has_no_sqli_fixer():
    code = "q = f\"SELECT * FROM u WHERE n = '{n}'\"\n"
    new_code, fixed = apply_fixes(code, builtin.scan(code, "python"))
    assert new_code == code and fixed == []


def test_ensure_import_after_existing_imports():
    lines = ["import os", "import sys", "", "x = 1"]
    assert ensure_import(lines, "import json")
    assert lines[2] == "import json"
    assert not ensure_import(lines, "import json")
