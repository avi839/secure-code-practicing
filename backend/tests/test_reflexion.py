from app.services.metrics_service import repair_regression
from app.services.prompts import build_reflection_prompt, format_findings
from app.services.providers.base import AIProvider, ProviderResult
from app.services.providers.demo import DemoProvider
from app.services.reflexion import SAME_CODE_EXPLANATION, ReflexionEngine
from app.services.scanner import ScannerService

scanner = ScannerService()
INSTRUCTION = "Reflect on each finding and identify the unsafe practice behind it."


class StubProvider(AIProvider):
    name = "stub"
    label = "Stub"
    model = "stub-1"

    def __init__(self, repaired_code):
        self.repaired_code = repaired_code
        self.prompts = []

    async def generate_code(self, task, language):
        return ProviderResult(code="x = 1\n", raw_response="x = 1\n", prompt="gen")

    async def repair_code(self, prompt, ctx):
        self.prompts.append(prompt)
        return ProviderResult(code=self.repaired_code, raw_response=self.repaired_code, prompt=prompt, tokens_used=3)


def test_reflection_prompt_contents():
    code = 'API_KEY = "abcdef123456"\nos.system(cmd)\n'
    findings = scanner.builtin.scan(code, "python")
    prompt = build_reflection_prompt("Run a command", "python", "t0", code, findings)
    assert "Run a command" in prompt and code in prompt and INSTRUCTION in prompt
    assert "(t0)" in prompt
    for f in findings:
        assert f"{f.cwe_id} {f.cwe_name} (line {f.start_line})" in prompt
    assert "CWE-798" in prompt and "(line 1)" in prompt and "CWE-78" in prompt and "(line 2)" in prompt
    assert format_findings([]) == "- No findings were reported."


async def test_demo_py_sqli_repairs_and_stops_early():
    engine = ReflexionEngine(DemoProvider(), scanner)
    seen = []

    async def on_round(result):
        seen.append(result.version)

    results = await engine.run("Look up a user by username in SQLite", "python", None, 3, on_round=on_round)
    assert [r.version for r in results] == ["t0", "t1", "t2"] == seen
    assert engine.stopped_early
    t0, t1, t2 = results
    assert t0.report.label == 1 and any(f.cwe_id == "CWE-89" for f in t0.report.findings)
    assert t1.findings_count < t0.findings_count
    assert t2.report.label == 0 and t2.findings_count == 0
    assert t1.diff and t1.diff.startswith("--- t0")
    assert "CWE-89" in t1.explanation and "Fixed 1 issue(s)" in t1.explanation
    assert any(item["cwe_id"] == "CWE-89" for item in t1.comparison["fixed"])
    assert "CWE-798" in t2.explanation
    m = repair_regression([t0.report.label], [t2.report.label], 2)
    assert m.repair_rate == 100.0 and not m.regression_defined


async def test_demo_js_xss_two_rounds():
    results = await ReflexionEngine(DemoProvider(), scanner).run(
        "Greet the user by name on an Express page", "javascript", None, 3)
    assert any(f.cwe_id == "CWE-79" for f in results[0].report.findings)
    assert results[-1].report.label == 0 and len(results) == 3


async def test_regression_scenario_detected():
    clean = "def add(a, b):\n    return a + b\n"
    provider = StubProvider("def add(a, b):\n    return eval(f'{a} + {b}')\n")
    engine = ReflexionEngine(provider, scanner)
    t0 = await engine.baseline("add numbers", "python", clean)
    assert t0.report.label == 0 and t0.prompt.startswith("User-supplied")
    t1 = await engine.reflect("add numbers", "python", t0)
    assert t1.report.label == 1
    assert [i["rule_id"] for i in t1.comparison["new"]] == ["PY-EVAL-001"]
    assert "Introduced 1 new issue(s)" in t1.explanation
    assert repair_regression([t0.report.label], [t1.report.label], 1).regression_rate == 100.0


async def test_unchanged_code_explanation_and_callback_stop():
    code = "import os\nos.system(cmd)\n"
    engine = ReflexionEngine(StubProvider(code), scanner)
    calls = []

    async def stop_after_first_reflection(result):
        calls.append(result.version)
        return result.round_number < 1

    results = await engine.run("run", "python", code, 5, on_round=stop_after_first_reflection)
    assert [r.version for r in results] == ["t0", "t1"] == calls
    assert results[1].explanation.startswith(SAME_CODE_EXPLANATION)
    assert results[1].diff == ""
    assert not engine.stopped_early


LOW_ONLY = "import pickle\n"  # Bandit B403 (LOW): labelled secure, but not finding-free


class ChangingStubProvider(StubProvider):
    """Returns a different (still LOW-only) revision every round."""

    async def repair_code(self, prompt, ctx):
        self.prompts.append(prompt)
        code = f"{ctx.previous_code}x{ctx.round_number} = {ctx.round_number}\n"
        return ProviderResult(code=code, raw_response=code, prompt=prompt)


async def test_secure_and_unchanged_stops_early():
    provider = StubProvider(LOW_ONLY)
    engine = ReflexionEngine(provider, scanner)
    results = await engine.run("load data", "python", LOW_ONLY, 5)
    assert results[0].report.label == 0 and results[0].findings_count >= 1
    assert [r.version for r in results] == ["t0", "t1"]
    assert len(provider.prompts) == 1 and engine.stopped_early


async def test_secure_and_changed_code_continues():
    provider = ChangingStubProvider("unused")
    engine = ReflexionEngine(provider, scanner)
    results = await engine.run("load data", "python", LOW_ONLY, 3)
    assert [r.version for r in results] == ["t0", "t1", "t2", "t3"]
    assert all(r.report.label == 0 and r.findings_count >= 1 for r in results)
    assert len(provider.prompts) == 3 and not engine.stopped_early


async def test_clean_baseline_stops_immediately():
    engine = ReflexionEngine(StubProvider("unused"), scanner)
    results = await engine.run("t", "python", "x = 1\n", 3)
    assert len(results) == 1 and engine.stopped_early
