"""
API tests. `with TestClient(app)` runs the lifespan (creates the tables) and executes
background tasks before the request returns, so evaluations are finished when POST returns.
"""

import asyncio
import logging
import os
import pathlib
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.services.evaluation_service as evaluation_service_module
from app.api import evaluations as evaluations_api
from app.config import Settings, settings
from app.database import AsyncSessionLocal, Base
from app.main import app
from app.models import Evaluation, User
from app.models.evaluation import EvaluationStatus
from app.services.evaluation_service import EvaluationService
from app.services.providers.base import AIProvider, ProviderError, ProviderResult

PY_SQLI = {"task": "Look up a user by username in SQLite", "language": "python", "ai_provider": "demo",
           "reflexion_rounds": 3}
JS_XSS = {"task": "Greet the user by name on an Express page", "language": "javascript", "ai_provider": "demo",
          "reflexion_rounds": 3}
USER_CODE = "import hashlib\n\n\ndef digest(data):\n    return hashlib.md5(data).hexdigest()\n"
SECRET_MARKER = "SECRET_MARKER_123"


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def _create(client, body):
    response = client.post("/api/evaluations", json=body)
    assert response.status_code == 201, response.text
    created = response.json()
    detail = client.get(f"/api/evaluations/{created['id']}")
    assert detail.status_code == 200
    return created, detail.json()


def _cwes(version):
    return {f["cwe_id"] for f in version["findings"]}


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["components"]["database"]["type"] == "sqlite"
    scanners = body["components"]["security_scanners"]
    assert scanners["builtin"] == "available" and scanners["semgrep"] == "not_integrated"
    assert body["components"]["ai_providers"]["demo"] == "available"
    assert response.headers.get("X-Request-ID")
    assert response.headers.get("X-Frame-Options") == "DENY"


def test_settings_read_only(client):
    body = client.get("/api/settings").json()
    assert body["rounds"] == {"min": 1, "max": 10, "default": 3}
    assert len(body["supported_languages"]) == 8
    assert {p["id"] for p in body["providers"]} >= {"openai", "anthropic", "google", "demo"}
    assert client.put("/api/settings", json={}).status_code == 405


def test_samples(client):
    samples = client.get("/api/samples").json()
    assert len(samples) >= 17
    assert {"id", "language", "title", "cwes", "task", "code"} <= set(samples[0])
    python_only = client.get("/api/samples", params={"language": "python"}).json()
    assert python_only and all(s["language"] == "python" for s in python_only)


def test_scan(client):
    code = 'import sqlite3\n\ndef find(cur, name):\n    return cur.execute(f"SELECT * FROM users WHERE name = \'{name}\'")\n'
    body = client.post("/api/scan", json={"code": code, "language": "python"}).json()
    assert body["label"] == 1 and body["is_secure"] is False
    sqli = next(f for f in body["findings"] if f["cwe_id"] == "CWE-89")
    assert sqli["cwe_url"] == "https://cwe.mitre.org/data/definitions/89.html"
    assert sqli["start_line"] == 4 and sqli["description"] and sqli["remediation"]
    assert set(body["severity_counts"]) == {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
    assert "builtin" in body["analyzers_run"]

    clean = client.post("/api/scan", json={"code": "x = 1\n", "language": "python"}).json()
    assert clean["is_secure"] is True and clean["findings"] == []


def test_python_sqli_evaluation(client):
    created, detail = _create(client, PY_SQLI)
    assert created["status"] == "pending" and created["is_demo"] is True
    assert detail["status"] == "completed", detail["error_message"]
    versions = detail["code_versions"]
    assert [v["version"] for v in versions] == ["t0", "t1", "t2"]
    t0, final = versions[0], versions[-1]
    assert t0["findings_count"] >= 1 and "CWE-89" in _cwes(t0) and t0["is_secure"] is False
    assert versions[1]["findings_count"] < t0["findings_count"]
    assert final["findings_count"] == 0 and final["is_secure"] is True and final["security_label"] == 0
    assert versions[1]["diff"].startswith("--- t0") and "CWE-89" in versions[1]["explanation"]
    assert any(item["cwe_id"] == "CWE-89" for item in versions[1]["comparison"]["fixed"])
    finding = next(f for f in t0["findings"] if f["cwe_id"] == "CWE-89")
    assert finding["cwe_url"].endswith("/89.html") and finding["status"] == "open"

    assert detail["stopped_early"] is True
    assert detail["completed_rounds"] == 2 and detail["requested_rounds"] == 3
    assert detail["baseline_secure"] is False and detail["final_secure"] is True
    assert detail["total_findings_t0"] == t0["findings_count"] and detail["total_findings_final"] == 0
    assert detail["findings_fixed"] == t0["findings_count"] and detail["findings_new"] == 0
    assert "user_code" not in detail["ai_config"] and detail["ai_config"]["source"] == "generated"

    metrics = detail["metrics"]
    assert [m["version"] for m in metrics] == ["t1", "t2"]
    last = metrics[-1]
    assert last["repair_rate"] == 100 and last["regression_rate"] == 0 and last["net_gain"] == 100
    assert last["repair_defined"] is True and last["regression_defined"] is False

    code = client.get(f"/api/evaluations/{detail['id']}/code/t1")
    assert code.status_code == 200 and code.json()["version"] == "t1"
    assert client.get(f"/api/evaluations/{detail['id']}/code/t9").status_code == 404
    assert client.get(f"/api/evaluations/{detail['id']}/code/latest").status_code == 422


def test_javascript_xss_evaluation(client):
    _, detail = _create(client, JS_XSS)
    assert detail["status"] == "completed", detail["error_message"]
    versions = detail["code_versions"]
    assert "CWE-79" in _cwes(versions[0])
    assert versions[-1]["findings_count"] == 0 and versions[-1]["is_secure"] is True


def test_user_supplied_code(client):
    _, detail = _create(client, {"task": "Hash some data", "language": "python", "code": USER_CODE,
                                 "reflexion_rounds": 2})
    assert detail["status"] == "completed", detail["error_message"]
    assert detail["ai_config"]["source"] == "user_code" and "user_code" not in detail["ai_config"]
    t0 = detail["code_versions"][0]
    assert t0["code"] == USER_CODE and "CWE-327" in _cwes(t0)
    assert detail["code_versions"][-1]["is_secure"] is True
    assert "sha256" in detail["code_versions"][-1]["code"]


def test_provider_fallback_is_labelled(client):
    _, detail = _create(client, {**PY_SQLI, "ai_provider": "openai", "reflexion_rounds": 1})
    assert detail["is_demo"] is True and detail["ai_provider"] == "demo"
    assert detail["ai_config"]["requested_provider"] == "openai"
    assert detail["ai_config"]["fallback_reason"] == "OPENAI_API_KEY is not configured"
    assert detail["status"] == "completed" and detail["completed_rounds"] == 1


@pytest.mark.parametrize(
    "body",
    [
        {**PY_SQLI, "reflexion_rounds": 0},
        {**PY_SQLI, "reflexion_rounds": 11},
        {**PY_SQLI, "language": "cobol"},
        {**PY_SQLI, "code": SECRET_MARKER + "x" * 50001},
        {**PY_SQLI, "task": "ab"},
    ],
)
def test_validation_errors_are_sanitized(client, body):
    response = client.post("/api/evaluations", json={**body, "ai_model": None})
    assert response.status_code == 422
    payload = response.json()
    assert payload["detail"] == "Validation failed" and payload["errors"]
    assert all(set(e) == {"field", "message"} for e in payload["errors"])
    assert SECRET_MARKER not in response.text and "input" not in payload
    assert response.headers.get("X-Request-ID")


def test_unknown_evaluation_is_generic_404(client):
    unknown = "00000000-0000-0000-0000-000000000000"
    for response in (
        client.get(f"/api/evaluations/{unknown}"),
        client.post(f"/api/evaluations/{unknown}/cancel"),
        client.delete(f"/api/evaluations/{unknown}"),
    ):
        assert response.status_code == 404
        assert response.json() == {"detail": "Evaluation not found"}


def test_list_and_cancel_finished(client):
    created, _ = _create(client, {**JS_XSS, "reflexion_rounds": 1})
    listing = client.get("/api/evaluations", params={"page_size": 100}).json()
    assert listing["total"] >= 1 and any(item["id"] == created["id"] for item in listing["items"])
    filtered = client.get("/api/evaluations", params={"language": "javascript", "status": "completed"}).json()
    assert filtered["items"] and all(i["language"] == "javascript" for i in filtered["items"])
    assert client.get("/api/evaluations", params={"status": "bogus"}).status_code == 422
    assert client.post(f"/api/evaluations/{created['id']}/cancel").status_code == 409


def test_dashboard(client):
    _create(client, PY_SQLI)
    _create(client, JS_XSS)
    body = client.get("/api/analytics/dashboard").json()
    assert body["total_evaluations"] >= 2 and body["completed_evaluations"] >= 2
    assert body["reflexion_curve"] and body["reflexion_curve"][0]["version"] == "t0"
    # Repair@T over every completed evaluation in this module's DB (some ran only 1 round on purpose).
    done = client.get("/api/evaluations", params={"status": "completed", "page_size": 100}).json()["items"]
    insecure_t0 = [e for e in done if e["baseline_secure"] is False]
    expected = round(sum(1 for e in insecure_t0 if e["final_secure"]) / len(insecure_t0) * 100, 2)
    assert body["average_repair_rate"] == expected and body["metrics_flags"]["repair_defined"] is True
    assert body["reflexion_curve"][-1]["repair_rate"] == expected
    assert [s["severity"] for s in body["severity_distribution"]] == ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    assert sum(s["t0"] for s in body["severity_distribution"]) > 0
    cwes = {c["cwe_id"]: c for c in body["cwe_breakdown"]}
    assert {"CWE-89", "CWE-79"} <= set(cwes)
    assert cwes["CWE-89"]["fixed"] >= 1 and cwes["CWE-89"]["remaining"] == 0
    assert body["severity_by_round"][0]["version"] == "t0"
    assert body["recent_evaluations"] and body["evaluations_by_language"].get("python", 0) >= 1
    assert body["evaluations_by_status"].get("completed", 0) >= 2

    by_cwe = client.get("/api/analytics/by-cwe").json()
    assert any(row["cwe_id"] == "CWE-89" and row["fix_rate"] == 100 for row in by_cwe)
    by_language = client.get("/api/analytics/by-language").json()
    python = next(row for row in by_language if row["language"] == "python")
    assert python["final_secure_rate"] >= python["baseline_secure_rate"]


INSECURE_CODE = "import os\n\n\ndef run(cmd):\n    os.system(cmd)\n"


class StubProvider(AIProvider):
    """Generates insecure code and returns it unchanged on repair (unless a hook says otherwise)."""

    name = "demo"
    label = "Stub"
    model = "stub-1"

    def __init__(self, on_repair=None):
        self.on_repair = on_repair
        self.repair_calls = 0

    async def generate_code(self, task, language):
        return ProviderResult(code=INSECURE_CODE, raw_response=INSECURE_CODE, prompt="gen")

    async def repair_code(self, prompt, ctx):
        self.repair_calls += 1
        if self.on_repair is not None:
            await self.on_repair()
        return ProviderResult(code=ctx.previous_code, raw_response=ctx.previous_code, prompt=prompt)


def _use_stub(monkeypatch, stub):
    monkeypatch.setattr(evaluation_service_module, "get_provider", lambda *args, **kwargs: (stub, None))


def test_provider_error_marks_evaluation_failed(client, monkeypatch):
    async def fail():
        raise ProviderError("Stub returned HTTP 500")

    _use_stub(monkeypatch, StubProvider(on_repair=fail))
    _, detail = _create(client, {**PY_SQLI, "reflexion_rounds": 3})
    assert detail["status"] == "failed"
    assert detail["error_message"] == "Stub returned HTTP 500"
    assert [v["version"] for v in detail["code_versions"]] == ["t0"]
    assert detail["completed_at"] is not None


def test_internal_error_during_run_is_sanitized(client, monkeypatch):
    async def crash():
        raise RuntimeError(SECRET_MARKER)

    _use_stub(monkeypatch, StubProvider(on_repair=crash))
    _, detail = _create(client, {**PY_SQLI, "reflexion_rounds": 2})
    assert detail["status"] == "failed"
    assert detail["error_message"].startswith("Evaluation failed due to an internal error (request id ")
    assert SECRET_MARKER not in detail["error_message"]


def test_cancel_between_rounds_stops_the_run(client, monkeypatch):
    async def cancel_running():
        async with AsyncSessionLocal() as db:
            running = (
                await db.execute(select(Evaluation.id).where(Evaluation.status == EvaluationStatus.RUNNING))
            ).scalars().all()
            assert len(running) == 1
            assert await EvaluationService(db).cancel_evaluation(running[0], reason="Stopped by test") is True

    stub = StubProvider(on_repair=cancel_running)
    _use_stub(monkeypatch, stub)
    _, detail = _create(client, {**PY_SQLI, "reflexion_rounds": 5})
    assert detail["status"] == "cancelled" and detail["error_message"] == "Stopped by test"
    assert stub.repair_calls == 1  # the loop stopped instead of running all 5 rounds
    assert [v["version"] for v in detail["code_versions"]] == ["t0"]
    assert detail["completed_rounds"] == 0


def test_unhandled_error_returns_sanitized_500(client, monkeypatch, caplog):
    async def boom(*args, **kwargs):
        raise RuntimeError(SECRET_MARKER)

    monkeypatch.setattr(evaluations_api.EvaluationService, "list_evaluations", boom)
    raw_client = TestClient(app, raise_server_exceptions=False)
    with caplog.at_level(logging.ERROR, logger="app"):
        response = raw_client.get("/api/evaluations", headers={"X-Request-ID": "req-500-test"})
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error", "request_id": "req-500-test"}
    assert response.headers["X-Request-ID"] == "req-500-test"
    assert SECRET_MARKER not in response.text
    logged = [r for r in caplog.records if r.name == "app" and "Unhandled error" in r.getMessage()]
    assert logged and "request_id=req-500-test" in logged[0].getMessage()


async def test_demo_user_bootstrap_is_concurrency_safe():
    """Two first requests on an empty DB must both get the same demo user (no UNIQUE violation)."""
    fd, path = tempfile.mkstemp(prefix="srx_race_", suffix=".db")
    os.close(fd)
    engine = create_async_engine(f"sqlite+aiosqlite:///{pathlib.Path(path).as_posix()}", connect_args={"timeout": 15})
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        sessions = async_sessionmaker(engine, expire_on_commit=False)

        async def first_request():
            async with sessions() as db:
                return (await evaluations_api.get_current_user(db)).id

        ids = await asyncio.gather(*(first_request() for _ in range(4)))
        assert len(set(ids)) == 1
        async with sessions() as db:
            assert (await db.execute(select(func.count(User.id)))).scalar() == 1
    finally:
        await engine.dispose()
        os.remove(path)


def test_null_origin_is_opt_in(client):
    assert "null" not in settings.cors_origins and settings.ALLOW_NULL_ORIGIN is False
    assert "null" in Settings(ALLOW_NULL_ORIGIN=True).cors_origins
    preflight = client.options(
        "/api/health", headers={"Origin": "null", "Access-Control-Request-Method": "GET"}
    )
    assert preflight.status_code == 400
    assert "access-control-allow-origin" not in client.get("/api/health", headers={"Origin": "null"}).headers


def test_delete_then_404(client):
    created, _ = _create(client, {**PY_SQLI, "reflexion_rounds": 1})
    response = client.delete(f"/api/evaluations/{created['id']}")
    assert response.status_code == 200 and response.json()["evaluation_id"] == created["id"]
    assert client.get(f"/api/evaluations/{created['id']}").status_code == 404
    assert client.get(f"/api/evaluations/{created['id']}/code/t0").status_code == 404
