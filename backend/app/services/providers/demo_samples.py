"""
Curated demo samples: realistic vulnerable code (stage 0) and its progressively
repaired versions. The last stage of every sample must scan clean (no finding of
MEDIUM or higher); tests/test_providers.py asserts this for every sample.
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


def _s(text: str) -> str:
    return text.lstrip("\n")


@dataclass
class DemoSample:
    id: str
    language: str
    title: str
    cwes: List[str]
    keywords: List[str]
    task: str
    stages: List[str]
    # stage_notes[k] explains what changed to produce stages[k] (stage_notes[0] describes the baseline).
    stage_notes: List[str] = field(default_factory=list)


# ======================================================================= Python
PY_SQLI = DemoSample(
    id="py-sqli",
    language="python",
    title="Flask user lookup (SQL injection + hard-coded secret)",
    cwes=["CWE-89", "CWE-798"],
    keywords=["sql", "database", "query", "username", "login", "look up a user", "lookup"],
    task="Look up a user by username in SQLite and return it as JSON from a Flask endpoint.",
    stages=[
        _s(r'''
import os
import sqlite3

from flask import Flask, jsonify

app = Flask(__name__)
SECRET_KEY = "dev-secret-key-123"
app.config["SECRET_KEY"] = SECRET_KEY

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/users/<username>")
def get_user(username):
    conn = get_connection()
    try:
        query = f"SELECT id, username, email FROM users WHERE username = '{username}'"
        row = conn.execute(query).fetchone()
    finally:
        conn.close()
    if row is None:
        return jsonify({"error": "user not found"}), 404
    return jsonify(dict(row))


if __name__ == "__main__":
    app.run()
'''),
        _s(r'''
import os
import sqlite3

from flask import Flask, jsonify

app = Flask(__name__)
SECRET_KEY = "dev-secret-key-123"
app.config["SECRET_KEY"] = SECRET_KEY

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/users/<username>")
def get_user(username):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id, username, email FROM users WHERE username = ?", (username,)
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return jsonify({"error": "user not found"}), 404
    return jsonify(dict(row))


if __name__ == "__main__":
    app.run()
'''),
        _s(r'''
import os
import sqlite3

from flask import Flask, jsonify

app = Flask(__name__)
SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY environment variable is required")
app.config["SECRET_KEY"] = SECRET_KEY

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/users/<username>")
def get_user(username):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id, username, email FROM users WHERE username = ?", (username,)
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return jsonify({"error": "user not found"}), 404
    return jsonify(dict(row))


if __name__ == "__main__":
    app.run()
'''),
    ],
    stage_notes=[
        "Baseline: the query is built with an f-string and the Flask secret key is hard-coded.",
        "Replaced the f-string query with a parameterized query (? placeholder) so the username is "
        "passed as data, not SQL.",
        "Moved SECRET_KEY to the environment and fail fast when it is missing.",
    ],
)

PY_CMDI = DemoSample(
    id="py-cmdi",
    language="python",
    title="Ping endpoint (OS command injection)",
    cwes=["CWE-78"],
    keywords=["ping", "command", "shell", "host", "subprocess", "exec"],
    task="Create a Flask endpoint that pings a host supplied by the client and reports whether it is reachable.",
    stages=[
        _s(r'''
import subprocess

from flask import Flask, jsonify, request

app = Flask(__name__)


@app.route("/ping")
def ping():
    host = request.args.get("host", "")
    if not host:
        return jsonify({"error": "host is required"}), 400
    result = subprocess.run(f"ping -c 1 {host}", shell=True, capture_output=True, text=True, timeout=10)
    return jsonify(
        {
            "host": host,
            "reachable": result.returncode == 0,
            "output": result.stdout,
        }
    )


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run()
'''),
        _s(r'''
import ipaddress
import subprocess

from flask import Flask, jsonify, request

app = Flask(__name__)


def validate_host(value):
    """Accept only literal IPv4/IPv6 addresses."""
    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        return None


@app.route("/ping")
def ping():
    host = validate_host(request.args.get("host", ""))
    if host is None:
        return jsonify({"error": "host must be a valid IP address"}), 400
    result = subprocess.run(
        ["ping", "-c", "1", host], capture_output=True, text=True, timeout=10, check=False
    )
    return jsonify(
        {
            "host": host,
            "reachable": result.returncode == 0,
            "output": result.stdout,
        }
    )


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run()
'''),
    ],
    stage_notes=[
        "Baseline: the host is interpolated into a shell command run with shell=True.",
        "Validated the host with ipaddress.ip_address and passed an argument list to subprocess.run "
        "without a shell.",
    ],
)

PY_PATH = DemoSample(
    id="py-path",
    language="python",
    title="File download (path traversal)",
    cwes=["CWE-22"],
    keywords=["file", "download", "upload", "path", "directory", "read"],
    task="Serve files from an uploads directory by name through a Flask download endpoint.",
    stages=[
        _s(r'''
import os

from flask import Flask, abort, request

app = Flask(__name__)
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")


@app.route("/files")
def download():
    name = request.args.get("name", "")
    if not name:
        abort(400)
    full_path = os.path.join(UPLOAD_DIR, name)
    if not os.path.isfile(full_path):
        abort(404)
    with open(os.path.join(UPLOAD_DIR, name), "rb") as handle:
        data = handle.read()
    return data, 200, {"Content-Type": "application/octet-stream"}


@app.route("/files/list")
def list_files():
    return {"files": sorted(os.listdir(UPLOAD_DIR))}


if __name__ == "__main__":
    app.run()
'''),
        _s(r'''
import os

from flask import Flask, abort, request

app = Flask(__name__)
UPLOAD_DIR = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads"))


def safe_path(name):
    """Resolve name inside UPLOAD_DIR or return None if it escapes the directory."""
    candidate = os.path.realpath(os.path.join(UPLOAD_DIR, name))
    if os.path.commonpath([UPLOAD_DIR, candidate]) != UPLOAD_DIR:
        return None
    return candidate


@app.route("/files")
def download():
    name = request.args.get("name", "")
    full_path = safe_path(name) if name else None
    if full_path is None:
        abort(400)
    if not os.path.isfile(full_path):
        abort(404)
    with open(full_path, "rb") as handle:
        data = handle.read()
    return data, 200, {"Content-Type": "application/octet-stream"}


@app.route("/files/list")
def list_files():
    return {"files": sorted(os.listdir(UPLOAD_DIR))}


if __name__ == "__main__":
    app.run()
'''),
    ],
    stage_notes=[
        "Baseline: the requested name is joined to the upload directory without a containment check.",
        "Resolved the path with os.path.realpath and rejected it unless os.path.commonpath shows it "
        "stays inside UPLOAD_DIR.",
    ],
)

PY_DESER = DemoSample(
    id="py-deser",
    language="python",
    title="Profile API (insecure deserialization)",
    cwes=["CWE-502"],
    keywords=["pickle", "deserial", "serial", "profile", "load", "object"],
    task="Accept a user profile object in a POST request, store it in memory and return it on GET.",
    stages=[
        _s(r'''
import pickle

from flask import Flask, abort, jsonify, request

app = Flask(__name__)
PROFILES = {}


@app.route("/profiles", methods=["POST"])
def save_profile():
    profile = pickle.loads(request.data)
    user_id = profile["user_id"]
    PROFILES[user_id] = profile
    return jsonify({"saved": user_id}), 201


@app.route("/profiles/<user_id>")
def get_profile(user_id):
    profile = PROFILES.get(user_id)
    if profile is None:
        abort(404)
    return jsonify(profile)


@app.route("/profiles")
def list_profiles():
    return jsonify(sorted(PROFILES))


if __name__ == "__main__":
    app.run()
'''),
        _s(r'''
import json

from flask import Flask, abort, jsonify, request

app = Flask(__name__)
PROFILES = {}
ALLOWED_FIELDS = {"user_id": str, "display_name": str, "age": int}


def parse_profile(raw):
    """Parse JSON and accept only the expected fields and types."""
    data = json.loads(raw)
    if not isinstance(data, dict) or not isinstance(data.get("user_id"), str):
        raise ValueError("invalid profile")
    return {k: v for k, v in data.items() if k in ALLOWED_FIELDS and isinstance(v, ALLOWED_FIELDS[k])}


@app.route("/profiles", methods=["POST"])
def save_profile():
    try:
        profile = parse_profile(request.get_data(as_text=True))
    except ValueError:
        return jsonify({"error": "invalid profile"}), 400
    PROFILES[profile["user_id"]] = profile
    return jsonify({"saved": profile["user_id"]}), 201


@app.route("/profiles/<user_id>")
def get_profile(user_id):
    profile = PROFILES.get(user_id)
    if profile is None:
        abort(404)
    return jsonify(profile)


if __name__ == "__main__":
    app.run()
'''),
    ],
    stage_notes=[
        "Baseline: the request body is unpickled, which executes attacker-controlled code.",
        "Replaced pickle with json.loads and validated the allowed fields and their types.",
    ],
)

PY_CRYPTO = DemoSample(
    id="py-crypto",
    language="python",
    title="Password storage (weak hashing)",
    cwes=["CWE-327"],
    keywords=["password", "hash", "crypto", "md5", "register", "credential"],
    task="Register users and verify their passwords for login.",
    stages=[
        _s(r'''
import hashlib

USERS = {}


def hash_password(password):
    return hashlib.md5(password.encode("utf-8")).hexdigest()


def register(username, password):
    if username in USERS:
        raise ValueError("user already exists")
    if len(password) < 8:
        raise ValueError("password too short")
    USERS[username] = hash_password(password)


def verify(username, password):
    stored = USERS.get(username)
    if stored is None:
        return False
    return stored == hash_password(password)


if __name__ == "__main__":
    register("alice", input("new password: "))
    print("login ok:", verify("alice", input("password: ")))
'''),
        _s(r'''
import hashlib
import hmac
import os

ITERATIONS = 600_000
USERS = {}


def hash_password(password, salt=None):
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return salt, digest


def register(username, password):
    if username in USERS:
        raise ValueError("user already exists")
    if len(password) < 8:
        raise ValueError("password too short")
    USERS[username] = hash_password(password)


def verify(username, password):
    stored = USERS.get(username)
    if stored is None:
        return False
    salt, expected = stored
    _, actual = hash_password(password, salt)
    return hmac.compare_digest(expected, actual)


if __name__ == "__main__":
    register("alice", input("new password: "))
    print("login ok:", verify("alice", input("password: ")))
'''),
    ],
    stage_notes=[
        "Baseline: passwords are hashed with unsalted MD5.",
        "Switched to salted PBKDF2-HMAC-SHA256 (600,000 iterations) and constant-time comparison.",
    ],
)

PY_SECRETS = DemoSample(
    id="py-secrets",
    language="python",
    title="S3 report uploader (hard-coded AWS keys)",
    cwes=["CWE-798"],
    keywords=["aws", "s3", "secret", "key", "credential", "token", "upload report"],
    task="Upload generated report files to an S3 bucket.",
    stages=[
        _s(r'''
import os

import boto3

AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"
AWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
BUCKET = "reports-bucket"


def get_client():
    return boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name="us-east-1",
    )


def upload_report(local_path):
    key = "reports/" + os.path.basename(local_path)
    get_client().upload_file(local_path, BUCKET, key)
    return key


if __name__ == "__main__":
    import sys

    for report in sys.argv[1:]:
        print("uploaded", upload_report(report))
'''),
        _s(r'''
import os

import boto3

BUCKET = os.environ.get("REPORTS_BUCKET", "reports-bucket")


def get_client():
    # Credentials come from the standard AWS chain (environment variables,
    # shared config or an attached IAM role) instead of source code.
    return boto3.client("s3", region_name=os.environ.get("AWS_REGION", "us-east-1"))


def upload_report(local_path):
    key = "reports/" + os.path.basename(local_path)
    get_client().upload_file(local_path, BUCKET, key)
    return key


if __name__ == "__main__":
    import sys

    if not os.environ.get("AWS_ACCESS_KEY_ID") and not os.environ.get("AWS_PROFILE"):
        print("warning: no AWS credentials in the environment; relying on an IAM role")
    for report in sys.argv[1:]:
        print("uploaded", upload_report(report))
'''),
    ],
    stage_notes=[
        "Baseline: AWS access keys are hard-coded in the module.",
        "Removed the literal keys and let boto3 load credentials from the environment / IAM role.",
    ],
)

# =================================================================== JavaScript
JS_XSS = DemoSample(
    id="js-xss",
    language="javascript",
    title="Express greeting + comments (cross-site scripting)",
    cwes=["CWE-79"],
    keywords=["greet", "html", "xss", "comment", "render", "page", "display"],
    task="Greet the user by name on an Express page and render user comments in the browser.",
    stages=[
        _s(r'''
const express = require("express");

const app = express();
app.use(express.json());

const comments = [];

app.get("/greet", (req, res) => {
  res.send("<h1>Hello " + req.query.name + "</h1>");
});

app.post("/comments", (req, res) => {
  comments.push(String(req.body.text || ""));
  res.status(201).json({ count: comments.length });
});

app.get("/comments", (req, res) => {
  res.json(comments);
});

// Browser-side helper shipped in the client bundle.
function renderComment(container, comment) {
  const item = document.createElement("li");
  item.innerHTML = comment;
  container.appendChild(item);
}

module.exports = { app, renderComment };

if (require.main === module) {
  app.listen(3000, "127.0.0.1");
}
'''),
        _s(r'''
const express = require("express");

const app = express();
app.use(express.json());

const comments = [];

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

app.get("/greet", (req, res) => {
  res.send("<h1>Hello " + escapeHtml(req.query.name) + "</h1>");
});

app.post("/comments", (req, res) => {
  comments.push(String(req.body.text || ""));
  res.status(201).json({ count: comments.length });
});

app.get("/comments", (req, res) => {
  res.json(comments);
});

// Browser-side helper shipped in the client bundle.
function renderComment(container, comment) {
  const item = document.createElement("li");
  item.innerHTML = comment;
  container.appendChild(item);
}

module.exports = { app, renderComment, escapeHtml };

if (require.main === module) {
  app.listen(3000, "127.0.0.1");
}
'''),
        _s(r'''
const express = require("express");

const app = express();
app.use(express.json());

const comments = [];

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

app.get("/greet", (req, res) => {
  res.send("<h1>Hello " + escapeHtml(req.query.name) + "</h1>");
});

app.post("/comments", (req, res) => {
  comments.push(String(req.body.text || ""));
  res.status(201).json({ count: comments.length });
});

app.get("/comments", (req, res) => {
  res.json(comments);
});

// Browser-side helper shipped in the client bundle.
function renderComment(container, comment) {
  const item = document.createElement("li");
  item.textContent = comment;
  container.appendChild(item);
}

module.exports = { app, renderComment, escapeHtml };

if (require.main === module) {
  app.listen(3000, "127.0.0.1");
}
'''),
    ],
    stage_notes=[
        "Baseline: the name query parameter is concatenated into HTML and comments are written with innerHTML.",
        "Added escapeHtml() and encoded the name before building the greeting HTML.",
        "Rendered comments with textContent so the browser treats them as text, never markup.",
    ],
)

JS_SQLI = DemoSample(
    id="js-sqli",
    language="javascript",
    title="Product search (SQL injection)",
    cwes=["CWE-89"],
    keywords=["sql", "database", "query", "mysql", "product", "search"],
    task="List products of a given category from MySQL in an Express API.",
    stages=[
        _s(r'''
const express = require("express");
const mysql = require("mysql2");

const pool = mysql.createPool({
  host: process.env.DB_HOST || "127.0.0.1",
  user: process.env.DB_USER || "app",
  password: process.env.DB_PASSWORD,
  database: "shop",
});

const app = express();

app.get("/products", (req, res) => {
  const category = String(req.query.category || "");
  const sql = "SELECT id, name, price FROM products WHERE category = '" + category + "'";
  pool.query(sql, (err, rows) => {
    if (err) {
      return res.status(500).json({ error: "database error" });
    }
    return res.json(rows);
  });
});

app.get("/health", (req, res) => {
  res.json({ status: "ok" });
});

module.exports = app;

if (require.main === module) {
  app.listen(3000, "127.0.0.1");
}
'''),
        _s(r'''
const express = require("express");
const mysql = require("mysql2");

const pool = mysql.createPool({
  host: process.env.DB_HOST || "127.0.0.1",
  user: process.env.DB_USER || "app",
  password: process.env.DB_PASSWORD,
  database: "shop",
});

const app = express();

app.get("/products", (req, res) => {
  const category = String(req.query.category || "");
  const sql = "SELECT id, name, price FROM products WHERE category = ?";
  pool.query(sql, [category], (err, rows) => {
    if (err) {
      return res.status(500).json({ error: "database error" });
    }
    return res.json(rows);
  });
});

app.get("/health", (req, res) => {
  res.json({ status: "ok" });
});

module.exports = app;

if (require.main === module) {
  app.listen(3000, "127.0.0.1");
}
'''),
    ],
    stage_notes=[
        "Baseline: the category is concatenated into the SQL string.",
        "Used a ? placeholder and passed the category as a bound parameter.",
    ],
)

JS_CMDI = DemoSample(
    id="js-cmdi",
    language="javascript",
    title="Ping API (OS command injection)",
    cwes=["CWE-78"],
    keywords=["ping", "command", "shell", "exec", "host", "process"],
    task="Expose an Express endpoint that pings a host and returns the output.",
    stages=[
        _s(r'''
const express = require("express");
const { exec } = require("child_process");

const app = express();

app.get("/ping", (req, res) => {
  const host = String(req.query.host || "");
  if (!host) {
    return res.status(400).json({ error: "host is required" });
  }
  exec(`ping -c 1 ${host}`, { timeout: 10000 }, (error, stdout) => {
    res.json({
      host,
      reachable: !error,
      output: stdout,
    });
  });
  return undefined;
});

app.get("/health", (req, res) => {
  res.json({ status: "ok" });
});

module.exports = app;

if (require.main === module) {
  app.listen(3000, "127.0.0.1");
}
'''),
        _s(r'''
const express = require("express");
const net = require("net");
const { execFile } = require("child_process");

const app = express();

app.get("/ping", (req, res) => {
  const host = String(req.query.host || "");
  if (net.isIP(host) === 0) {
    return res.status(400).json({ error: "host must be a valid IP address" });
  }
  execFile("ping", ["-c", "1", host], { timeout: 10000 }, (error, stdout) => {
    res.json({
      host,
      reachable: !error,
      output: stdout,
    });
  });
  return undefined;
});

app.get("/health", (req, res) => {
  res.json({ status: "ok" });
});

module.exports = app;

if (require.main === module) {
  app.listen(3000, "127.0.0.1");
}
'''),
    ],
    stage_notes=[
        "Baseline: the host is interpolated into a shell command run by exec().",
        "Validated the host with net.isIP and used execFile with an argument array (no shell).",
    ],
)

JS_SECRETS_CRYPTO = DemoSample(
    id="js-secrets-crypto",
    language="javascript",
    title="Auth helpers (hard-coded API key + MD5)",
    cwes=["CWE-798", "CWE-327"],
    keywords=["password", "hash", "api key", "secret", "crypto", "md5", "auth", "token"],
    task="Write Node.js helpers that hash user passwords and check an API key header.",
    stages=[
        _s(r'''
const crypto = require("crypto");

const API_KEY = "live-3f9a1c7e5b2d4a60";
const users = new Map();

function hashPassword(password) {
  return crypto.createHash("md5").update(password).digest("hex");
}

function register(username, password) {
  if (users.has(username)) {
    throw new Error("user exists");
  }
  users.set(username, hashPassword(password));
}

function verify(username, password) {
  const stored = users.get(username);
  return stored !== undefined && stored === hashPassword(password);
}

function checkApiKey(req) {
  return req.headers["x-api-key"] === API_KEY;
}

module.exports = { register, verify, checkApiKey };
'''),
        _s(r'''
const crypto = require("crypto");

const API_KEY = process.env.API_KEY;
if (!API_KEY) {
  throw new Error("API_KEY environment variable is required");
}
const users = new Map();

function hashPassword(password, salt = crypto.randomBytes(16)) {
  const hash = crypto.scryptSync(password, salt, 64);
  return { salt, hash };
}

function register(username, password) {
  if (users.has(username)) {
    throw new Error("user exists");
  }
  users.set(username, hashPassword(password));
}

function verify(username, password) {
  const stored = users.get(username);
  if (stored === undefined) {
    return false;
  }
  const { hash } = hashPassword(password, stored.salt);
  return crypto.timingSafeEqual(hash, stored.hash);
}

function checkApiKey(req) {
  const given = Buffer.from(String(req.headers["x-api-key"] || ""));
  const expected = Buffer.from(API_KEY);
  return given.length === expected.length && crypto.timingSafeEqual(given, expected);
}

module.exports = { register, verify, checkApiKey };
'''),
    ],
    stage_notes=[
        "Baseline: the API key is hard-coded and passwords use unsalted MD5.",
        "Loaded the API key from process.env, hashed passwords with salted scrypt and compared in constant time.",
    ],
)

JS_PATH = DemoSample(
    id="js-path",
    language="javascript",
    title="Static file route (path traversal)",
    cwes=["CWE-22"],
    keywords=["file", "download", "path", "directory", "static", "sendfile"],
    task="Serve files from a files directory by name with Express.",
    stages=[
        _s(r'''
const express = require("express");
const fs = require("fs");
const path = require("path");

const app = express();
const FILES_DIR = path.join(__dirname, "files");

app.get("/files/:name", (req, res) => {
  res.sendFile(path.join(__dirname, "files", req.params.name), (err) => {
    if (err) {
      res.status(404).json({ error: "not found" });
    }
  });
});

app.get("/files", (req, res) => {
  fs.readdir(FILES_DIR, (err, names) => {
    if (err) {
      return res.status(500).json({ error: "cannot list files" });
    }
    return res.json(names);
  });
});

module.exports = app;

if (require.main === module) {
  app.listen(3000, "127.0.0.1");
}
'''),
        _s(r'''
const express = require("express");
const fs = require("fs");
const path = require("path");

const app = express();
const FILES_DIR = path.resolve(__dirname, "files");

app.get("/files/:name", (req, res) => {
  const filePath = path.resolve(FILES_DIR, req.params.name);
  if (!filePath.startsWith(FILES_DIR + path.sep)) {
    return res.status(400).json({ error: "invalid file name" });
  }
  return res.sendFile(filePath, (err) => {
    if (err) {
      res.status(404).json({ error: "not found" });
    }
  });
});

app.get("/files", (req, res) => {
  fs.readdir(FILES_DIR, (err, names) => {
    if (err) {
      return res.status(500).json({ error: "cannot list files" });
    }
    return res.json(names);
  });
});

module.exports = app;

if (require.main === module) {
  app.listen(3000, "127.0.0.1");
}
'''),
    ],
    stage_notes=[
        "Baseline: the requested name is joined into the path without checking where it resolves.",
        "Resolved the path and rejected it unless it stays inside FILES_DIR.",
    ],
)

# ====================================================== Other languages (2 stages)
JAVA_SAMPLE = DemoSample(
    id="java-secrets-crypto",
    language="java",
    title="JDBC login (hard-coded DB password + MD5)",
    cwes=["CWE-798", "CWE-327"],
    keywords=["login", "password", "jdbc", "database", "hash", "user"],
    task="Check a username and password against the users table over JDBC.",
    stages=[
        _s(r'''
import java.math.BigInteger;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;

public class UserRepository {
    private static final String DB_URL = "jdbc:postgresql://localhost:5432/app";
    private static final String DB_USER = "app";
    private static final String DB_PASSWORD = "Sup3rS3cret!";

    public boolean checkLogin(String username, String candidate) throws Exception {
        MessageDigest md = MessageDigest.getInstance("MD5");
        byte[] digest = md.digest(candidate.getBytes(StandardCharsets.UTF_8));
        String hash = new BigInteger(1, digest).toString(16);
        try (Connection conn = DriverManager.getConnection(DB_URL, DB_USER, DB_PASSWORD);
             PreparedStatement ps = conn.prepareStatement(
                 "SELECT password_hash FROM users WHERE username = ?")) {
            ps.setString(1, username);
            try (ResultSet rs = ps.executeQuery()) {
                return rs.next() && rs.getString(1).equals(hash);
            }
        }
    }
}
'''),
        _s(r'''
import java.security.MessageDigest;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import javax.crypto.SecretKeyFactory;
import javax.crypto.spec.PBEKeySpec;

public class UserRepository {
    private static final String DB_URL = System.getenv("DB_URL");
    private static final String DB_USER = System.getenv("DB_USER");
    private static final String DB_PASSWORD = System.getenv("DB_PASSWORD");
    private static final int ITERATIONS = 210_000;

    public boolean checkLogin(String username, String candidate) throws Exception {
        try (Connection conn = DriverManager.getConnection(DB_URL, DB_USER, DB_PASSWORD);
             PreparedStatement ps = conn.prepareStatement(
                 "SELECT password_hash, salt FROM users WHERE username = ?")) {
            ps.setString(1, username);
            try (ResultSet rs = ps.executeQuery()) {
                if (!rs.next()) {
                    return false;
                }
                PBEKeySpec spec = new PBEKeySpec(candidate.toCharArray(), rs.getBytes(2), ITERATIONS, 256);
                byte[] actual = SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256")
                    .generateSecret(spec).getEncoded();
                return MessageDigest.isEqual(actual, rs.getBytes(1));
            }
        }
    }
}
'''),
    ],
    stage_notes=[
        "Baseline: the database password is hard-coded and passwords are hashed with MD5.",
        "Read DB credentials from the environment and verified passwords with salted PBKDF2-HMAC-SHA256 "
        "using a constant-time comparison.",
    ],
)

C_SAMPLE = DemoSample(
    id="c-bof",
    language="c",
    title="User record (buffer overflow)",
    cwes=["CWE-120"],
    keywords=["buffer", "string", "copy", "name", "user"],
    task="Store a user name passed on the command line in a fixed-size struct and print it.",
    stages=[
        _s(r'''
#include <stdio.h>
#include <string.h>

#define NAME_MAX_LEN 32

typedef struct {
    char name[NAME_MAX_LEN];
    int age;
} user_t;

void set_user_name(user_t *user, const char *input) {
    strcpy(user->name, input);
}

int main(int argc, char **argv) {
    user_t user;
    memset(&user, 0, sizeof(user));
    if (argc < 2) {
        fprintf(stderr, "usage: %s <name>\n", argv[0]);
        return 1;
    }
    set_user_name(&user, argv[1]);
    user.age = 30;
    printf("Hello, %s (age %d)\n", user.name, user.age);
    return 0;
}
'''),
        _s(r'''
#include <stdio.h>
#include <string.h>

#define NAME_MAX_LEN 32

typedef struct {
    char name[NAME_MAX_LEN];
    int age;
} user_t;

void set_user_name(user_t *user, const char *input) {
    /* snprintf never writes past the buffer and always NUL-terminates. */
    snprintf(user->name, sizeof(user->name), "%s", input);
}

int main(int argc, char **argv) {
    user_t user;
    memset(&user, 0, sizeof(user));
    if (argc < 2) {
        fprintf(stderr, "usage: %s <name>\n", argv[0]);
        return 1;
    }
    set_user_name(&user, argv[1]);
    user.age = 30;
    printf("Hello, %s (age %d)\n", user.name, user.age);
    return 0;
}
'''),
    ],
    stage_notes=[
        "Baseline: strcpy copies unbounded input into a 32-byte buffer.",
        "Replaced strcpy with snprintf bounded by sizeof(user->name).",
    ],
)

CPP_SAMPLE = DemoSample(
    id="cpp-bof",
    language="cpp",
    title="Greeter (sprintf buffer overflow)",
    cwes=["CWE-120"],
    keywords=["greet", "buffer", "string", "format", "name"],
    task="Write a C++ greeter class that prints a greeting for a name passed on the command line.",
    stages=[
        _s(r'''
#include <cstdio>
#include <iostream>
#include <string>
#include <utility>

class Greeter {
public:
    explicit Greeter(std::string prefix) : prefix_(std::move(prefix)) {}

    void greet(const char *name) const {
        char buffer[64];
        sprintf(buffer, "%s, %s!", prefix_.c_str(), name);
        std::cout << buffer << std::endl;
    }

private:
    std::string prefix_;
};

int main(int argc, char **argv) {
    if (argc < 2) {
        std::cerr << "usage: greeter <name>" << std::endl;
        return 1;
    }
    Greeter greeter("Hello");
    greeter.greet(argv[1]);
    return 0;
}
'''),
        _s(r'''
#include <iostream>
#include <string>
#include <utility>

class Greeter {
public:
    explicit Greeter(std::string prefix) : prefix_(std::move(prefix)) {}

    void greet(const std::string &name) const {
        // std::string grows as needed, so there is no fixed-size buffer to overflow.
        const std::string message = prefix_ + ", " + name + "!";
        std::cout << message << std::endl;
    }

private:
    std::string prefix_;
};

int main(int argc, char **argv) {
    if (argc < 2) {
        std::cerr << "usage: greeter <name>" << std::endl;
        return 1;
    }
    Greeter greeter("Hello");
    greeter.greet(argv[1]);
    return 0;
}
'''),
    ],
    stage_notes=[
        "Baseline: sprintf writes an unbounded name into a 64-byte stack buffer.",
        "Built the message with std::string instead of a fixed-size buffer.",
    ],
)

CSHARP_SAMPLE = DemoSample(
    id="csharp-secrets-crypto",
    language="csharp",
    title="Account service (connection-string password + MD5)",
    cwes=["CWE-798", "CWE-327"],
    keywords=["password", "hash", "account", "connection", "database", "user"],
    task="Write a C# account service that hashes passwords and checks whether a user exists.",
    stages=[
        _s(r'''
using System;
using System.Data.SqlClient;
using System.Security.Cryptography;
using System.Text;

public class AccountService
{
    private const string ConnectionString =
        "Server=db.internal;Database=accounts;User Id=app;Password=Winter2024!;";

    public static string HashPassword(string candidate)
    {
        using (var md5 = MD5.Create())
        {
            byte[] digest = md5.ComputeHash(Encoding.UTF8.GetBytes(candidate));
            return Convert.ToBase64String(digest);
        }
    }

    public static bool UserExists(string username)
    {
        using (var conn = new SqlConnection(ConnectionString))
        using (var cmd = new SqlCommand("SELECT COUNT(*) FROM Users WHERE Username = @username", conn))
        {
            cmd.Parameters.AddWithValue("@username", username);
            conn.Open();
            return (int)cmd.ExecuteScalar() > 0;
        }
    }
}
'''),
        _s(r'''
using System;
using System.Data.SqlClient;
using System.Security.Cryptography;
using System.Text;

public class AccountService
{
    private static readonly string ConnectionString =
        Environment.GetEnvironmentVariable("ACCOUNTS_DB_CONNECTION")
        ?? throw new InvalidOperationException("ACCOUNTS_DB_CONNECTION is not set");

    public static string HashPassword(string candidate)
    {
        byte[] salt = RandomNumberGenerator.GetBytes(16);
        byte[] hash = Rfc2898DeriveBytes.Pbkdf2(
            Encoding.UTF8.GetBytes(candidate), salt, 210000, HashAlgorithmName.SHA256, 32);
        return Convert.ToBase64String(salt) + ":" + Convert.ToBase64String(hash);
    }

    public static bool UserExists(string username)
    {
        using (var conn = new SqlConnection(ConnectionString))
        using (var cmd = new SqlCommand("SELECT COUNT(*) FROM Users WHERE Username = @username", conn))
        {
            cmd.Parameters.AddWithValue("@username", username);
            conn.Open();
            return (int)cmd.ExecuteScalar() > 0;
        }
    }
}
'''),
    ],
    stage_notes=[
        "Baseline: the connection string embeds a password and passwords are hashed with MD5.",
        "Loaded the connection string from the environment and hashed passwords with salted PBKDF2-SHA256.",
    ],
)

PHP_SAMPLE = DemoSample(
    id="php-sqli",
    language="php",
    title="Product lookup (SQL injection)",
    cwes=["CWE-89"],
    keywords=["sql", "database", "query", "mysql", "product", "lookup"],
    task="Return a product as JSON by the id given in the query string using mysqli.",
    stages=[
        _s(r'''
<?php
header("Content-Type: application/json");

$mysqli = new mysqli("127.0.0.1", "app", getenv("DB_PASSWORD"), "shop");
if ($mysqli->connect_errno) {
    http_response_code(500);
    exit(json_encode(["error" => "database unavailable"]));
}

$id = $_GET["id"] ?? "";
$result = mysqli_query($mysqli, "SELECT id, name, price FROM products WHERE id = " . $id);
if ($result === false) {
    http_response_code(500);
    exit(json_encode(["error" => "query failed"]));
}

$product = mysqli_fetch_assoc($result);
if ($product === null) {
    http_response_code(404);
    exit(json_encode(["error" => "not found"]));
}

echo json_encode($product);
$mysqli->close();
'''),
        _s(r'''
<?php
header("Content-Type: application/json");

$mysqli = new mysqli("127.0.0.1", "app", getenv("DB_PASSWORD"), "shop");
if ($mysqli->connect_errno) {
    http_response_code(500);
    exit(json_encode(["error" => "database unavailable"]));
}

$id = filter_input(INPUT_GET, "id", FILTER_VALIDATE_INT);
if ($id === false || $id === null) {
    http_response_code(400);
    exit(json_encode(["error" => "id must be an integer"]));
}

$stmt = $mysqli->prepare("SELECT id, name, price FROM products WHERE id = ?");
$stmt->bind_param("i", $id);
$stmt->execute();
$product = $stmt->get_result()->fetch_assoc();
if ($product === null) {
    http_response_code(404);
    exit(json_encode(["error" => "not found"]));
}

echo json_encode($product);
$mysqli->close();
'''),
    ],
    stage_notes=[
        "Baseline: the id from $_GET is concatenated into the SQL string.",
        "Validated the id as an integer and used a prepared statement with bind_param.",
    ],
)

RUST_SAMPLE = DemoSample(
    id="rust-sqli-secrets",
    language="rust",
    title="User lookup (format! SQL + hard-coded API key)",
    cwes=["CWE-89", "CWE-798"],
    keywords=["sql", "database", "query", "user", "api key", "lookup"],
    task="Look up a user by name with rusqlite and authorize requests with an API key.",
    stages=[
        _s(r'''
use rusqlite::{Connection, Result};

const API_KEY: &str = "prod-4f6c2a9e8b1d7350";

pub struct User {
    pub id: i64,
    pub name: String,
}

pub fn find_user(conn: &Connection, name: &str) -> Result<Option<User>> {
    let sql = format!("SELECT id, name FROM users WHERE name = '{}'", name);
    let mut stmt = conn.prepare(&sql)?;
    let mut rows = stmt.query([])?;
    match rows.next()? {
        Some(row) => Ok(Some(User {
            id: row.get(0)?,
            name: row.get(1)?,
        })),
        None => Ok(None),
    }
}

pub fn authorize(header: &str) -> bool {
    header == API_KEY
}

fn main() -> Result<()> {
    let conn = Connection::open("users.db")?;
    let user = find_user(&conn, "alice")?;
    println!("found: {}", user.is_some());
    Ok(())
}
'''),
        _s(r'''
use rusqlite::{params, Connection, Result};
use std::env;

pub struct User {
    pub id: i64,
    pub name: String,
}

pub fn find_user(conn: &Connection, name: &str) -> Result<Option<User>> {
    let mut stmt = conn.prepare("SELECT id, name FROM users WHERE name = ?1")?;
    let mut rows = stmt.query(params![name])?;
    match rows.next()? {
        Some(row) => Ok(Some(User {
            id: row.get(0)?,
            name: row.get(1)?,
        })),
        None => Ok(None),
    }
}

pub fn authorize(header: &str) -> bool {
    match env::var("API_KEY") {
        Ok(expected) => !expected.is_empty() && header == expected,
        Err(_) => false,
    }
}

fn main() -> Result<()> {
    let conn = Connection::open("users.db")?;
    let user = find_user(&conn, "alice")?;
    println!("found: {}", user.is_some());
    Ok(())
}
'''),
    ],
    stage_notes=[
        "Baseline: the SQL is built with format! and the API key is hard-coded.",
        "Bound the name with a ?1 parameter and read the API key from the environment.",
    ],
)

SAMPLES: List[DemoSample] = [
    PY_SQLI, PY_CMDI, PY_PATH, PY_DESER, PY_CRYPTO, PY_SECRETS,
    JS_XSS, JS_SQLI, JS_CMDI, JS_SECRETS_CRYPTO, JS_PATH,
    JAVA_SAMPLE, C_SAMPLE, CPP_SAMPLE, CSHARP_SAMPLE, PHP_SAMPLE, RUST_SAMPLE,
]
SAMPLES_BY_ID = {sample.id: sample for sample in SAMPLES}


def samples_for(language: str) -> List[DemoSample]:
    return [s for s in SAMPLES if s.language == (language or "").lower()]


def select_sample(language: str, task: str) -> Optional[DemoSample]:
    """First sample of the language whose keyword appears in the task, else the first sample of the language."""
    candidates = samples_for(language)
    if not candidates:
        return None
    text = (task or "").lower()
    for sample in candidates:
        # Keywords match at a word start ("file" matches "files" but not "profile").
        if any(re.search(r"\b" + re.escape(keyword), text) for keyword in sample.keywords):
            return sample
    return candidates[0]


_WS = re.compile(r"\s+")


def _normalize(code: str) -> str:
    return _WS.sub(" ", code or "").strip()


_STAGE_INDEX = {_normalize(stage): (sample, index) for sample in SAMPLES for index, stage in enumerate(sample.stages)}


def find_stage(code: str) -> Optional[Tuple[DemoSample, int]]:
    """Return (sample, stage_index) if the code matches a curated stage (whitespace-insensitive)."""
    return _STAGE_INDEX.get(_normalize(code))
