import json
import logging

import httpx
import pytest

from app.config import settings
from app.services.prompts import SYSTEM_PROMPT
from app.services.providers import ProviderError, RepairContext, extract_code, get_provider, provider_status
from app.services.providers.anthropic_provider import AnthropicProvider
from app.services.providers.demo import DemoProvider
from app.services.providers.demo_samples import SAMPLES, find_stage, select_sample
from app.services.providers.gemini_provider import GeminiProvider
from app.services.providers.openai_provider import OpenAIProvider
from app.services.scanner import ScannerService
from app.services.scanner.findings import severity_rank

scanner = ScannerService()
FAKE_KEY = "sk-test-SECRET-0123456789"
MEDIUM = severity_rank("MEDIUM")


def _medium_plus(code, language):
    return [f for f in scanner.scan(code, language).findings if severity_rank(f.severity) >= MEDIUM]


@pytest.mark.parametrize("sample", SAMPLES, ids=[s.id for s in SAMPLES])
def test_demo_sample_stages(sample):
    assert len(sample.stages) >= 2
    assert len(sample.stage_notes) == len(sample.stages)
    assert _medium_plus(sample.stages[0], sample.language), f"{sample.id} stage 0 must be insecure"
    assert not _medium_plus(sample.stages[-1], sample.language), f"{sample.id} last stage must be clean"
    for stage in sample.stages:
        assert 20 <= len(stage.splitlines()) <= 45


def test_required_samples_present():
    ids = {s.id for s in SAMPLES}
    assert {"py-sqli", "py-cmdi", "py-path", "py-deser", "py-crypto", "py-secrets",
            "js-xss", "js-sqli", "js-cmdi", "js-secrets-crypto", "js-path"} <= ids
    assert {s.language for s in SAMPLES} == {"python", "javascript", "java", "c", "cpp", "csharp", "php", "rust"}
    by_id = {s.id: s for s in SAMPLES}
    assert len(by_id["py-sqli"].stages) == 3 and len(by_id["js-xss"].stages) == 3


def test_select_sample_keyword_routing():
    assert select_sample("python", "Look up a user by username in SQLite").id == "py-sqli"
    assert select_sample("python", "Ping a host from Flask").id == "py-cmdi"
    assert select_sample("python", "Deserialize a pickle profile").id == "py-deser"
    assert select_sample("javascript", "Greet the user by name on an Express page").id == "js-xss"
    assert select_sample("javascript", "something unrelated").id == "js-xss"
    assert select_sample("cobol", "anything") is None


def test_find_stage_is_whitespace_insensitive():
    sample = SAMPLES[0]
    assert find_stage("\n\n" + sample.stages[1].replace("\n", "\r\n") + "  ") == (sample, 1)
    assert find_stage("print('hello')") is None


def test_extract_code():
    assert extract_code("Here:\n```python\nx = 1\n```\nbye") == "x = 1"
    assert extract_code("```\na\nb\n```") == "a\nb"
    assert extract_code("  plain code  ") == "plain code"
    assert extract_code("") == ""


def test_factory_falls_back_when_keys_blank():
    for requested, key in (("openai", "OPENAI_API_KEY"), ("anthropic", "ANTHROPIC_API_KEY"),
                           ("google", "GOOGLE_API_KEY")):
        provider, reason = get_provider(requested)
        assert provider.is_demo and reason == f"{key} is not configured"
    provider, reason = get_provider("demo")
    assert provider.is_demo and reason is None


def test_factory_demo_mode_forces_demo(monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", FAKE_KEY)
    monkeypatch.setattr(settings, "DEMO_MODE", True)
    provider, reason = get_provider("openai")
    assert provider.is_demo and reason == "DEMO_MODE is enabled"
    assert all(p["effective"] == "demo-forced" for p in provider_status() if p["id"] != "demo")


def test_factory_live_provider_with_key(monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", FAKE_KEY)
    provider, reason = get_provider("openai", None)
    assert isinstance(provider, OpenAIProvider) and reason is None
    assert provider.model == settings.OPENAI_MODEL
    provider, _ = get_provider("openai", "gpt-custom")
    assert provider.model == "gpt-custom"
    status = {p["id"]: p for p in provider_status()}
    assert status["openai"]["effective"] == "live" and status["anthropic"]["effective"] == "demo-fallback"
    assert FAKE_KEY not in json.dumps(provider_status())


# --------------------------------------------------------------- HTTP providers
def _capture(response_json, status=200):
    seen = []

    def handler(request: httpx.Request):
        seen.append(request)
        return httpx.Response(status, json=response_json)

    return seen, httpx.MockTransport(handler)


async def test_openai_request_shape():
    seen, transport = _capture({"choices": [{"message": {"content": "```python\nx = 1\n```"}}],
                                "usage": {"total_tokens": 42}})
    provider = OpenAIProvider(api_key=FAKE_KEY, model="gpt-4o-mini", transport=transport)
    result = await provider.generate_code("add numbers", "python")
    req = seen[0]
    body = json.loads(req.content)
    assert str(req.url) == "https://api.openai.com/v1/chat/completions"
    assert req.headers["authorization"] == f"Bearer {FAKE_KEY}"
    assert body["model"] == "gpt-4o-mini" and body["temperature"] == 0.2
    assert body["max_tokens"] == settings.MAX_TOKENS
    assert body["messages"][0] == {"role": "system", "content": SYSTEM_PROMPT}
    assert "add numbers" in body["messages"][1]["content"]
    assert result.code == "x = 1" and result.tokens_used == 42


async def test_anthropic_request_shape():
    seen, transport = _capture({"content": [{"type": "text", "text": "```js\nlet a;\n```"}],
                                "usage": {"input_tokens": 10, "output_tokens": 5}})
    provider = AnthropicProvider(api_key=FAKE_KEY, model="claude-x", transport=transport)
    ctx = RepairContext(task="t", language="javascript", previous_code="var a;", previous_version="t0")
    result = await provider.repair_code("fix it", ctx)
    req = seen[0]
    body = json.loads(req.content)
    assert str(req.url) == "https://api.anthropic.com/v1/messages"
    assert req.headers["x-api-key"] == FAKE_KEY and req.headers["anthropic-version"] == "2023-06-01"
    assert body["system"] == SYSTEM_PROMPT and body["messages"] == [{"role": "user", "content": "fix it"}]
    assert body["model"] == "claude-x" and body["max_tokens"] == settings.MAX_TOKENS
    assert result.code == "let a;" and result.tokens_used == 15


async def test_gemini_key_only_in_header():
    seen, transport = _capture({"candidates": [{"content": {"parts": [{"text": "int x;"}]}}],
                                "usageMetadata": {"totalTokenCount": 7}})
    provider = GeminiProvider(api_key=FAKE_KEY, model="gemini-1.5-flash", transport=transport)
    result = await provider.generate_code("declare x", "c")
    req = seen[0]
    body = json.loads(req.content)
    assert str(req.url) == ("https://generativelanguage.googleapis.com/v1beta/models/"
                            "gemini-1.5-flash:generateContent")
    assert FAKE_KEY not in str(req.url)
    assert req.headers["x-goog-api-key"] == FAKE_KEY
    assert body["systemInstruction"]["parts"][0]["text"] == SYSTEM_PROMPT
    assert body["contents"][0]["role"] == "user" and "declare x" in body["contents"][0]["parts"][0]["text"]
    assert body["generationConfig"]["temperature"] == 0.2
    assert result.code == "int x;" and result.tokens_used == 7


@pytest.mark.parametrize("cls,label", [(OpenAIProvider, "OpenAI"), (AnthropicProvider, "Anthropic"),
                                       (GeminiProvider, "Gemini")])
async def test_http_error_is_sanitized(cls, label, caplog):
    caplog.set_level(logging.DEBUG)
    _, transport = _capture({"error": {"message": f"Invalid key {FAKE_KEY} BODY-DETAIL"}}, status=401)
    provider = cls(api_key=FAKE_KEY, transport=transport, retry_delay=0)
    with pytest.raises(ProviderError) as info:
        await provider.generate_code("task", "python")
    message = str(info.value)
    assert message == f"{label} request failed (HTTP 401)"
    assert "BODY-DETAIL" not in message and FAKE_KEY not in message
    assert FAKE_KEY not in caplog.text and "task" not in caplog.text


async def test_retry_once_on_server_error():
    calls = []

    def handler(request):
        calls.append(1)
        if len(calls) == 1:
            return httpx.Response(503, json={})
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    provider = OpenAIProvider(api_key=FAKE_KEY, transport=httpx.MockTransport(handler), retry_delay=0)
    result = await provider.generate_code("t", "python")
    assert len(calls) == 2 and result.code == "ok" and result.tokens_used is None


async def test_timeout_and_network_errors():
    def timeout(request):
        raise httpx.ReadTimeout("slow", request=request)

    def network(request):
        raise httpx.ConnectError("down", request=request)

    with pytest.raises(ProviderError, match=r"OpenAI request failed \(timeout\)"):
        await OpenAIProvider(api_key=FAKE_KEY, transport=httpx.MockTransport(timeout), retry_delay=0) \
            .generate_code("t", "python")
    with pytest.raises(ProviderError, match=r"OpenAI request failed \(network error\)"):
        await OpenAIProvider(api_key=FAKE_KEY, transport=httpx.MockTransport(network), retry_delay=0) \
            .generate_code("t", "python")


async def test_malformed_response():
    _, transport = _capture({"unexpected": True})
    with pytest.raises(ProviderError, match="unexpected response"):
        await OpenAIProvider(api_key=FAKE_KEY, transport=transport).generate_code("t", "python")


# ------------------------------------------------------------------ demo provider
async def test_demo_generate_and_progressive_repair():
    provider = DemoProvider()
    t0 = await provider.generate_code("Look up a user by username in SQLite", "python")
    sample = select_sample("python", "Look up a user by username in SQLite")
    assert t0.code == sample.stages[0] and t0.tokens_used > 0 and provider.model == "securereflex-demo-1"
    ctx = RepairContext(task="x", language="python", previous_code=t0.code, previous_version="t0")
    t1 = await provider.repair_code("prompt", ctx)
    assert t1.code == sample.stages[1] and t1.notes == sample.stage_notes[1]
    ctx.previous_code = sample.stages[-1]
    last = await provider.repair_code("prompt", ctx)
    assert last.code == sample.stages[-1]


async def test_demo_autofix_one_tier_per_round():
    code = 'import os\nos.system(cmd)\nh = hashlib.md5(b)\n'
    findings = scanner.builtin.scan(code, "python")
    ctx = RepairContext(task="x", language="python", previous_code=code, previous_version="t0", findings=findings)
    result = await DemoProvider().repair_code("p", ctx)
    assert "subprocess.run(shlex.split(cmd), check=True)" in result.code
    assert "hashlib.md5(" in result.code  # HIGH tier waits for the next round
    assert "CRITICAL" in result.notes


async def test_demo_reports_unfixable():
    code = "q = f\"SELECT * FROM u WHERE n = '{n}'\"\n"
    findings = scanner.builtin.scan(code, "python")
    ctx = RepairContext(task="x", language="python", previous_code=code, previous_version="t0", findings=findings)
    result = await DemoProvider().repair_code("p", ctx)
    assert result.code == code
    assert "cannot auto-repair PY-SQLI-001" in result.notes and "real AI provider" in result.notes
