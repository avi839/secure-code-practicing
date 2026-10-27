"""
Built-in static analysis rules (regex based, line oriented).

Each rule has positive and negative unit tests in tests/test_scanner.py.
Patterns are deliberately conservative: a match means the line uses an
API or construct that is a well-known source of the given CWE.
"""

import re
from dataclasses import dataclass, field
from typing import List, Pattern, Set

I = re.IGNORECASE

ALL_LANGUAGES = {"c", "cpp", "csharp", "java", "javascript", "python", "php", "rust"}
GENERIC_LANGUAGES = {"java", "c", "cpp", "csharp", "php", "rust"}

# SQL statement shapes (keyword combinations, so prose such as "select a file" does not match).
_SQL = r"(?:\bSELECT\s.+?\sFROM\b|\bINSERT\s+INTO\b|\bUPDATE\s+[\w.`\"\[\]]+\s+SET\b|\bDELETE\s+FROM\b)"

_SECRET_NAME = r"(?:password|passwd|pwd|secret|api_?key|apikey|token|access_?key|private_?key)"


@dataclass
class Rule:
    id: str
    languages: Set[str]
    cwe_id: str
    cwe_name: str
    severity: str
    confidence: str
    title: str
    patterns: List[Pattern[str]]
    why: str
    fix: str
    # Suppress the rule for the whole file when ALL of these match somewhere in the file
    # (e.g. a path-containment check is present).
    suppress_if_file_matches: List[Pattern[str]] = field(default_factory=list)
    # A matching line is ignored when ANY of these match the same line.
    line_excludes: List[Pattern[str]] = field(default_factory=list)

    def applies_to(self, language: str) -> bool:
        return "*" in self.languages or language in self.languages


def _p(*patterns: str, flags: int = 0) -> List[Pattern[str]]:
    return [re.compile(p, flags) for p in patterns]


CWE_89 = ("CWE-89", "SQL Injection")
CWE_78 = ("CWE-78", "OS Command Injection")
CWE_22 = ("CWE-22", "Path Traversal")
CWE_502 = ("CWE-502", "Deserialization of Untrusted Data")
CWE_327 = ("CWE-327", "Use of a Broken or Risky Cryptographic Algorithm")
CWE_798 = ("CWE-798", "Use of Hard-coded Credentials")
CWE_95 = ("CWE-95", "Eval Injection")
CWE_79 = ("CWE-79", "Cross-site Scripting (XSS)")
CWE_120 = ("CWE-120", "Classic Buffer Overflow")

_SQLI_WHY = (
    "The SQL statement is built by inserting variable data directly into the query text. "
    "An attacker who controls that data can change the structure of the query and read, "
    "modify or delete data they should not reach."
)
_CMDI_WHY = (
    "The command is executed through a shell or built from variable data. Shell metacharacters "
    "such as ';', '&&' or '|' in that data let an attacker run arbitrary commands on the server."
)
_PATH_WHY = (
    "A file path is derived from variable input without verifying that the resolved path stays "
    "inside the intended directory. Sequences such as '../' let an attacker read or overwrite "
    "arbitrary files."
)
_DESER_WHY = (
    "Deserializing untrusted data with this API can instantiate arbitrary objects and execute "
    "code during loading, so a crafted payload leads to remote code execution."
)
_CRYPTO_WHY = (
    "This algorithm is cryptographically broken: practical collision or key-recovery attacks exist, "
    "and fast unsalted hashes let attackers brute-force passwords offline."
)
_SECRET_WHY = (
    "A credential is hard-coded in source code. Anyone with access to the code, its history or "
    "the built artifact can extract it, and rotating it requires a code change."
)
_EVAL_WHY = (
    "Evaluating dynamically built code executes whatever the input contains. If any part of the "
    "string is attacker-controlled, this is arbitrary code execution."
)
_XSS_WHY = (
    "Untrusted data is written into HTML without context-aware encoding. A value containing "
    "markup or <script> runs in the victim's browser and can steal sessions or act as the user."
)

RULES: List[Rule] = [
    # ------------------------------------------------------------------ Python
    Rule(
        id="PY-SQLI-001", languages={"python"}, cwe_id=CWE_89[0], cwe_name=CWE_89[1],
        severity="CRITICAL", confidence="HIGH",
        title="SQL query built with string formatting",
        patterns=_p(
            rf"^(?=.*\b(?:f|rf|fr)[\"'])(?=.*{_SQL})(?=.*\{{)",
            rf"^(?=.*{_SQL})(?=.*[\"']\s*%\s*[\w(\[])",
            rf"^(?=.*{_SQL})(?=.*(?:[\"']\s*\+\s*\w|\w\s*\+\s*[\"']))",
            rf"^(?=.*{_SQL})(?=.*[\"']\.format\()",
            flags=I,
        ),
        why=_SQLI_WHY,
        fix=(
            "Use a parameterized query: keep the SQL text constant with placeholders "
            "(cursor.execute(\"SELECT ... WHERE name = ?\", (name,))) and pass values separately."
        ),
    ),
    Rule(
        id="PY-CMDI-001", languages={"python"}, cwe_id=CWE_78[0], cwe_name=CWE_78[1],
        severity="CRITICAL", confidence="HIGH",
        title="Command executed through a shell",
        patterns=_p(r"\bshell\s*=\s*True\b", r"\bos\.system\(", r"\bos\.popen\("),
        why=_CMDI_WHY,
        fix=(
            "Call subprocess.run() with an argument list and shell=False (the default), validate the "
            "input against an allow-list (e.g. ipaddress.ip_address for hosts), and never build "
            "command strings from user data."
        ),
    ),
    Rule(
        id="PY-PATH-001", languages={"python"}, cwe_id=CWE_22[0], cwe_name=CWE_22[1],
        severity="HIGH", confidence="MEDIUM",
        title="File opened with a non-literal path",
        patterns=_p(r"(?<![.\w])open\(\s*(?![\"')])\S", r"\bsend_file\(\s*(?![\"')])\S"),
        why=_PATH_WHY,
        fix=(
            "Resolve the path with os.path.realpath()/Path.resolve() and verify it stays inside the "
            "base directory (os.path.commonpath([base, path]) == base or Path.is_relative_to) "
            "before opening it; reject names containing path separators."
        ),
        suppress_if_file_matches=_p(r"realpath|resolve\(", r"startswith|commonpath|is_relative_to"),
    ),
    Rule(
        id="PY-DESER-001", languages={"python"}, cwe_id=CWE_502[0], cwe_name=CWE_502[1],
        severity="CRITICAL", confidence="HIGH",
        title="Unsafe deserialization",
        patterns=_p(
            r"\b(?:c?[Pp]ickle|dill|shelve)\.loads?\(",
            r"\bmarshal\.loads?\(",
            r"\byaml\.load\((?!.*SafeLoader)",
            r"\byaml\.unsafe_load\(",
            r"\bjsonpickle\.decode\(",
        ),
        why=_DESER_WHY,
        fix=(
            "Use a data-only format such as json.loads() and validate the resulting structure; for "
            "YAML use yaml.safe_load(). Never unpickle data that crosses a trust boundary."
        ),
    ),
    Rule(
        id="PY-CRYPTO-001", languages={"python"}, cwe_id=CWE_327[0], cwe_name=CWE_327[1],
        severity="HIGH", confidence="HIGH",
        title="Weak cryptographic algorithm",
        patterns=_p(
            r"\bhashlib\.(?:md5|sha1)\(",
            r"\bhashlib\.new\(\s*[\"'](?:md5|sha1)[\"']",
            r"\bDES\.new\(",
            r"\bARC4\.new\(",
            flags=0,
        ),
        why=_CRYPTO_WHY,
        fix=(
            "Use SHA-256 or stronger for integrity checks; for passwords use a slow salted KDF such "
            "as hashlib.pbkdf2_hmac('sha256', pw, salt, 600_000), scrypt or argon2; use AES-GCM "
            "instead of DES/RC4."
        ),
        line_excludes=_p(r"usedforsecurity\s*=\s*False"),
    ),
    Rule(
        id="PY-SECRET-001", languages={"python"}, cwe_id=CWE_798[0], cwe_name=CWE_798[1],
        severity="HIGH", confidence="MEDIUM",
        title="Hard-coded secret",
        patterns=_p(rf"{_SECRET_NAME}\w*\s*=\s*[\"'][^\"']{{6,}}[\"']", flags=I),
        why=_SECRET_WHY,
        fix=(
            "Load the secret at runtime from the environment or a secrets manager "
            "(os.environ[\"NAME\"]) and keep it out of version control."
        ),
    ),
    Rule(
        id="PY-EVAL-001", languages={"python"}, cwe_id=CWE_95[0], cwe_name=CWE_95[1],
        severity="HIGH", confidence="MEDIUM",
        title="Dynamic code evaluation",
        patterns=_p(r"(?<![.\w])eval\(", r"(?<![.\w])exec\("),
        why=_EVAL_WHY,
        fix=(
            "Parse data with json.loads() or ast.literal_eval() for literals, or dispatch through an "
            "explicit allow-list of functions instead of evaluating code."
        ),
    ),
    Rule(
        id="PY-XSS-001", languages={"python"}, cwe_id=CWE_79[0], cwe_name=CWE_79[1],
        severity="HIGH", confidence="MEDIUM",
        title="HTML built from unescaped data",
        patterns=_p(
            r"\brender_template_string\(\s*(?![\"')])\S",
            r"\breturn\s+f[\"']\s*<\w[^\"']*\{",
            r"\breturn\s+[\"']\s*<\w[^\"']*[\"']\s*\+",
            r"\bMarkup\(\s*(?![\"')])\S",
        ),
        why=_XSS_WHY,
        fix=(
            "Render through a template with auto-escaping (render_template with a .html file) or "
            "escape values with markupsafe.escape()/html.escape() before inserting them into HTML."
        ),
        line_excludes=_p(r"\bescape\("),
    ),
    # -------------------------------------------------------------- JavaScript
    Rule(
        id="JS-XSS-001", languages={"javascript"}, cwe_id=CWE_79[0], cwe_name=CWE_79[1],
        severity="HIGH", confidence="MEDIUM",
        title="Untrusted data written into HTML",
        patterns=_p(
            r"\.(?:inner|outer)HTML\s*\+?=(?!\s*(?:\"[^\"]*\"|'[^']*'|`[^`$]*`)\s*;?\s*$)",
            r"\bdocument\.write(?:ln)?\(",
            r"\.insertAdjacentHTML\(",
            r"\bres\.(?:send|write|end)\((?=.*\breq\.)(?=.*(?:\+|\$\{))",
        ),
        why=_XSS_WHY,
        fix=(
            "Use textContent / createTextNode for text, escape HTML special characters before "
            "building markup on the server (or use a templating engine that auto-escapes), and "
            "sanitize with DOMPurify when HTML is genuinely required."
        ),
        line_excludes=_p(r"\bescape\w*\(|encodeURIComponent\(|DOMPurify\.sanitize\(", flags=I),
    ),
    Rule(
        id="JS-SQLI-001", languages={"javascript"}, cwe_id=CWE_89[0], cwe_name=CWE_89[1],
        severity="CRITICAL", confidence="HIGH",
        title="SQL query built by string concatenation",
        patterns=_p(rf"^(?=.*{_SQL})(?=.*(?:[\"'`]\s*\+|\+\s*[\"'`]|\$\{{))", flags=I),
        why=_SQLI_WHY,
        fix=(
            "Use placeholders and pass values separately: db.query(\"SELECT ... WHERE id = ?\", [id]) "
            "(mysql/sqlite) or $1 parameters (pg)."
        ),
    ),
    Rule(
        id="JS-CMDI-001", languages={"javascript"}, cwe_id=CWE_78[0], cwe_name=CWE_78[1],
        severity="CRITICAL", confidence="HIGH",
        title="Shell command built from variable data",
        patterns=_p(r"\b(?:exec|execSync)\((?=.*(?:\$\{|[\"'`]\s*\+|\+\s*[\"'`]))"),
        why=_CMDI_WHY,
        fix=(
            "Use execFile()/spawn() with an argument array (no shell) and validate the input against "
            "an allow-list (e.g. net.isIP for hosts)."
        ),
    ),
    Rule(
        id="JS-PATH-001", languages={"javascript"}, cwe_id=CWE_22[0], cwe_name=CWE_22[1],
        severity="HIGH", confidence="MEDIUM",
        title="File path built from request data",
        patterns=_p(r"\b(?:readFile(?:Sync)?|createReadStream|sendFile)\((?=.*(?:\breq\.|\+|\$\{))"),
        why=_PATH_WHY,
        fix=(
            "Resolve the path with path.resolve(BASE_DIR, name) and reject it unless it "
            "startsWith(BASE_DIR + path.sep); prefer an allow-list of file names."
        ),
        suppress_if_file_matches=_p(r"path\.resolve|path\.normalize", r"startsWith"),
    ),
    Rule(
        id="JS-SECRET-001", languages={"javascript"}, cwe_id=CWE_798[0], cwe_name=CWE_798[1],
        severity="HIGH", confidence="MEDIUM",
        title="Hard-coded secret",
        patterns=_p(
            rf"\b(?:const|let|var)\s+\w*{_SECRET_NAME}\w*\s*=\s*[\"'`][^\"'`]{{6,}}[\"'`]",
            rf"\b\w*{_SECRET_NAME}\w*[\"']?\s*:\s*[\"'`][^\"'`]{{6,}}[\"'`]",
            flags=I,
        ),
        why=_SECRET_WHY,
        fix="Read the secret from process.env (or a secrets manager) at startup and fail fast if it is missing.",
    ),
    Rule(
        id="JS-CRYPTO-001", languages={"javascript"}, cwe_id=CWE_327[0], cwe_name=CWE_327[1],
        severity="HIGH", confidence="HIGH",
        title="Weak cryptographic algorithm",
        patterns=_p(r"\bcreateHash\(\s*[\"'`](?:md5|sha1)[\"'`]", r"\bcreateCipher\(", flags=I),
        why=_CRYPTO_WHY,
        fix=(
            "Use crypto.createHash('sha256') for integrity, crypto.scryptSync/pbkdf2 with a random "
            "salt for passwords, and createCipheriv('aes-256-gcm', key, iv) for encryption."
        ),
    ),
    Rule(
        id="JS-EVAL-001", languages={"javascript"}, cwe_id=CWE_95[0], cwe_name=CWE_95[1],
        severity="HIGH", confidence="MEDIUM",
        title="Dynamic code evaluation",
        patterns=_p(r"(?<![.\w])eval\(", r"\bnew\s+Function\("),
        why=_EVAL_WHY,
        fix="Parse data with JSON.parse() and dispatch through an explicit allow-list instead of evaluating code.",
    ),
    Rule(
        id="JS-DESER-001", languages={"javascript"}, cwe_id=CWE_502[0], cwe_name=CWE_502[1],
        severity="CRITICAL", confidence="HIGH",
        title="Unsafe deserialization",
        patterns=_p(r"\bunserialize\(", r"node-serialize"),
        why=_DESER_WHY,
        fix="Use JSON.parse() on untrusted input and validate the result against a schema.",
    ),
    # --------------------------------------------- Java / C / C++ / C# / PHP / Rust
    Rule(
        id="GEN-SECRET-001", languages=GENERIC_LANGUAGES, cwe_id=CWE_798[0], cwe_name=CWE_798[1],
        severity="HIGH", confidence="MEDIUM",
        title="Hard-coded secret",
        patterns=_p(
            rf"{_SECRET_NAME}\w*[\"']?(?:\s*:\s*&(?:'static\s+)?str)?\s*(?:=>|=)\s*@?[\"'][^\"']{{6,}}[\"']",
            r"[\"'][^\"']*\b(?:password|pwd)=(?![{$%])[^;\"'\s]{3,}",
            flags=I,
        ),
        why=_SECRET_WHY,
        fix=(
            "Read the credential from the environment or a secrets manager at runtime "
            "(System.getenv, Environment.GetEnvironmentVariable, getenv, std::env::var) and "
            "keep it out of source control and connection strings."
        ),
    ),
    Rule(
        id="GEN-CRYPTO-001", languages=GENERIC_LANGUAGES, cwe_id=CWE_327[0], cwe_name=CWE_327[1],
        severity="HIGH", confidence="HIGH",
        title="Weak cryptographic algorithm",
        patterns=_p(
            r"getInstance\(\s*\"(?:MD5|SHA-?1|DES)(?:/[^\"]*)?\"",
            r"\b(?:MD5|SHA1)\.Create\(",
            r"\bnew\s+(?:MD5|SHA1)CryptoServiceProvider\b",
            r"(?<![\w>.:])(?:md5|sha1)\(",
            r"\bMd5::new\b",
            r"\bmd5::compute\(",
            r"\b(?:MD5|SHA1)_Init\(",
            r"\b(?:MD5|SHA1)\(",
        ),
        why=_CRYPTO_WHY,
        fix=(
            "Use SHA-256 or stronger for integrity; for passwords use a salted adaptive KDF "
            "(PBKDF2, bcrypt, scrypt, Argon2 / password_hash() in PHP); use AES-GCM instead of DES."
        ),
    ),
    Rule(
        id="GEN-SQLI-001", languages=GENERIC_LANGUAGES, cwe_id=CWE_89[0], cwe_name=CWE_89[1],
        severity="CRITICAL", confidence="HIGH",
        title="SQL query built by string concatenation or interpolation",
        patterns=_p(
            rf"^(?=.*{_SQL})(?=.*(?:[\"']\s*\+\s*\w|\w\s*\+\s*[\"']|[\"']\s*\.\s*\$|\$\w+(?:\[[^\]]*\])?\s*\.\s*[\"']|\$\"|\{{\$|format!\(|\bs?n?printf\())",
            r"\"\s*(?:SELECT|INSERT|UPDATE|DELETE)\b[^\"]*\$[A-Za-z_{]",
            flags=I,
        ),
        why=_SQLI_WHY,
        fix=(
            "Use prepared statements with bound parameters (PreparedStatement / SqlParameter / "
            "mysqli prepare + bind_param / PDO / sqlx bind) and keep the SQL text constant."
        ),
    ),
    Rule(
        id="C-BOF-001", languages={"c", "cpp"}, cwe_id=CWE_120[0], cwe_name=CWE_120[1],
        severity="HIGH", confidence="HIGH",
        title="Unbounded buffer copy",
        patterns=_p(r"\b(?:strcpy|strcat|sprintf|vsprintf|gets)\(", r"\bscanf\(\s*\"%s\""),
        why=(
            "This function writes into a fixed-size buffer without checking the destination size. "
            "Input longer than the buffer overwrites adjacent memory, which can crash the program "
            "or let an attacker hijack control flow."
        ),
        fix=(
            "Use bounded alternatives (snprintf, strncpy/strlcpy with explicit termination, fgets) "
            "and always pass sizeof(buffer); in C++ prefer std::string."
        ),
    ),
    Rule(
        id="C-CMDI-001", languages={"c", "cpp"}, cwe_id=CWE_78[0], cwe_name=CWE_78[1],
        severity="CRITICAL", confidence="MEDIUM",
        title="Shell command built from variable data",
        patterns=_p(r"(?<![\w.>:])(?:system|popen)\(\s*(?![\")])\S"),
        why=_CMDI_WHY,
        fix="Use execv()/posix_spawn() with an argument vector instead of a shell, and validate input against an allow-list.",
    ),
    Rule(
        id="JAVA-CMDI-001", languages={"java"}, cwe_id=CWE_78[0], cwe_name=CWE_78[1],
        severity="CRITICAL", confidence="HIGH",
        title="Command built by string concatenation",
        patterns=_p(r"Runtime\.getRuntime\(\)\.exec\((?=.*\+)"),
        why=_CMDI_WHY,
        fix="Use new ProcessBuilder(List.of(\"ping\", \"-c\", \"1\", host)) with validated arguments and no shell.",
    ),
    Rule(
        id="PHP-CMDI-001", languages={"php"}, cwe_id=CWE_78[0], cwe_name=CWE_78[1],
        severity="CRITICAL", confidence="HIGH",
        title="Shell command built from variable data",
        patterns=_p(r"\b(?:shell_exec|system|exec|passthru|popen|proc_open)\((?=[^)]*\$)"),
        why=_CMDI_WHY,
        fix="Avoid the shell; if unavoidable wrap every argument in escapeshellarg() and validate it against an allow-list.",
        line_excludes=_p(r"escapeshellarg\("),
    ),
    Rule(
        id="PHP-XSS-001", languages={"php"}, cwe_id=CWE_79[0], cwe_name=CWE_79[1],
        severity="HIGH", confidence="HIGH",
        title="Request data echoed without encoding",
        patterns=_p(r"\b(?:echo|print)\b(?=.*\$_(?:GET|POST|REQUEST|COOKIE))(?!.*(?:htmlspecialchars|htmlentities))"),
        why=_XSS_WHY,
        fix="Encode output with htmlspecialchars($value, ENT_QUOTES, 'UTF-8') before echoing it.",
    ),
]

RULES_BY_ID = {rule.id: rule for rule in RULES}
