# SecureReflex AI

Secure code generation with reflexion-based vulnerability repair.

SecureReflex AI generates (or accepts) code, scans it with static analysis, feeds the findings back to an AI model and asks it to repair the code. It repeats this for a configurable number of rounds and measures how security changes from the baseline `t0` to every later version `t1..tN`. The workflow is inspired by ["Secure Code Generation at Scale with Reflexion"](https://arxiv.org/abs/2511.03898) (arXiv 2511.03898). This project is not affiliated with the paper's authors.

> Automated static analysis cannot guarantee that code is secure. Treat the results as review aids, not proof.

## Contents

- [Architecture](#architecture)
- [Quick start](#quick-start)
- [Manual run](#manual-run)
- [Configuration](#configuration)
- [Demo mode and provider fallback](#demo-mode-and-provider-fallback)
- [Security scanners](#security-scanners)
- [Metrics](#metrics)
- [API](#api)
- [Tests](#tests)
- [Docker](#docker)
- [Security notes](#security-notes)
- [Next steps](#next-steps)

## Architecture

```
Browser ──► Next.js 14 (frontend/, :3000) ──/api/* rewrite──► FastAPI (backend/, :8000) ──► SQLite / PostgreSQL
                                                                 │
                                                                 ├─ Reflexion engine  (generate t0 → scan → reflect → repair → rescan)
                                                                 ├─ Scanners          (built-in rules, 8 languages + Bandit for Python)
                                                                 ├─ AI providers      (OpenAI, Anthropic, Gemini via httpx, deterministic demo)
                                                                 └─ Metrics           (Repair@t, Regression@t, NetGain@t vs t0)
```

- Backend: FastAPI, async SQLAlchemy 2, Pydantic v2, SQLite (`aiosqlite`) by default. Evaluations run as background tasks and commit after every round, so the UI can show rounds as they finish.
- Frontend: Next.js 14 app router, TypeScript, Tailwind and recharts. Pages: Home (`/`), Workbench (`/workbench`), Dashboard (`/dashboard`) and History (`/history`). The browser only calls same-origin `/api/*`. Next.js proxies those calls to `BACKEND_URL`.
- Prompts live only in `backend/app/services/prompts.py`. They are derived from arXiv 2511.03898 and are not claimed to be verbatim. Check the wording against the paper PDF.

```
backend/app/
  main.py               app, middleware (request id, security headers), error handlers, routers
  config.py             settings (see Configuration)
  api/                  health, settings, scan, evaluations, analytics
  services/
    scanner/            built-in rules, Bandit runner, merge/dedupe
    providers/          demo, openai, anthropic, gemini, factory
    reflexion.py        pure reflexion engine (no DB)
    metrics_service.py  pure metric functions
    evaluation_service.py / analytics_service.py   persistence and aggregation
    prompts.py          the only place prompt text lives
backend/tests/          pytest suite
frontend/src/           app/ pages, components/, lib/ (API client, types, formatting)
```

## Quick start

Prerequisites: Python 3.10+, Node.js 18+ (20 LTS recommended), and the backend venv at `backend\venv` (see [Manual run](#manual-run) for one-time setup).

From the repository root, run one of these:

```bat
START.bat
```

```powershell
.\START.ps1                 # optional: -BackendPort 8000 -FrontendPort 3005 -NoBrowser
```

Both launchers:

1. Check that `backend\venv\Scripts\python.exe` exists and that `aiosqlite` is installed. If either is missing, they print the command that fixes it.
2. Warn if port 8000 is already in use (for example by another backend).
3. Pick the frontend port: the first free port from 3000 to 3010 (`START.ps1 -FrontendPort N` forces a port). Another service may already use 3000 (Grafana does by default). In that case the launcher prints the port it chose, for example `[INFO] ... The frontend will use port 3001.`
4. Open a "SecureReflex Backend" window: `uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --reload-dir app`.
5. Wait up to 40 s for `GET /api/health`.
6. Run `npm ci` only if `frontend\node_modules` is missing, then open a "SecureReflex Frontend" window: `npm run dev -- -p <port>`.
7. Open `http://localhost:<port>` and print it as `Frontend : http://localhost:<port>`.

To stop, close both windows or press Ctrl+C in each.

| URL | What |
|-----|------|
| http://localhost:3000 (or the port the launcher printed) | Web app |
| http://127.0.0.1:8000/docs | Interactive API docs (Swagger UI) |
| http://127.0.0.1:8000/api/health | Health check |

## Manual run

One-time backend setup:

```powershell
cd backend
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt        # runtime
.\venv\Scripts\python.exe -m pip install -r requirements-dev.txt    # optional: tests and linters
```

Backend:

```powershell
cd backend
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --reload-dir app
```

Frontend (in a second terminal):

```powershell
cd frontend
npm ci                          # only the first time
npm run dev -- -p 3000          # development (use another port, e.g. 3001, if 3000 is taken)
# or a production build:
npm run build
npm run start -- -p 3000
```

If http://localhost:3000 shows a different application (for example a Grafana login page), another service already owns port 3000. Start the frontend with `-p 3001` and open that port instead.

The frontend proxies `/api/*` to `BACKEND_URL` (default `http://127.0.0.1:8000`). Rewrites are fixed at build time, so set `BACKEND_URL` before `npm run build` (in the shell or in `frontend\.env.local`; see `frontend\.env.local.example`). Use `127.0.0.1` rather than `localhost`. Newer Node versions resolve `localhost` to `::1`, and uvicorn listens on IPv4.

## Configuration

Settings are read from environment variables, then from `.env` in the repository root, then from `backend/.env`. Copy `.env.example` to `.env` to start. Unknown keys are ignored, so old `.env` files still load.

| Variable | Default | Notes |
|----------|---------|-------|
| `ENVIRONMENT` | `development` | `development`, `production` or `test`. Selects text (development) or JSON logs. |
| `DEBUG` / `SQL_ECHO` | `false` | `SQL_ECHO` logs SQL statements. |
| `LOG_LEVEL` | `INFO` | Logs are plain text in development and JSON otherwise. |
| `DATABASE_URL` | `sqlite+aiosqlite:///<backend>/data/securereflex.db` | Relative SQLite paths resolve against `backend/`. PostgreSQL: `postgresql+asyncpg://user:pass@host:5432/db`. |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `GOOGLE_API_KEY` | blank | Blank means "not configured". |
| `OPENAI_MODEL` | `gpt-4o-mini` | Check the current model ids with each vendor. |
| `ANTHROPIC_MODEL` | `claude-3-5-sonnet-latest` | |
| `GEMINI_MODEL` | `gemini-1.5-flash` | |
| `DEFAULT_AI_PROVIDER` | `demo` | `openai`, `anthropic`, `google` or `demo`. |
| `AI_TIMEOUT_SECONDS` / `MAX_TOKENS` | `60` / `4096` | Per provider request. |
| `DEMO_MODE` | `false` | `true` forces the demo provider for every evaluation. |
| `DEMO_LATENCY_MS` | `350` | Simulated latency per demo call. |
| `BANDIT_ENABLED` | `true` | Bandit runs on Python code when it is installed. |
| `SCANNER_TIMEOUT_SECONDS` | `30` | Bandit subprocess timeout. |
| `DEFAULT_REFLEXION_ROUNDS` | `3` | Clamped to 1..10. |
| `MAX_CODE_CHARS` / `MAX_TASK_CHARS` | `50000` / `5000` | Request validation limits. |
| `CORS_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001` | Comma-separated. The Next.js proxy does not need CORS. |
| `ALLOW_NULL_ORIGIN` | `false` | `true` also allows CORS origin `null`, which browsers send for pages opened from `file://` and for sandboxed iframes. Sandboxed iframes on any website can send it, so only enable it when you need it. |

Frontend: `BACKEND_URL` (build time) sets the proxy target.

## Demo mode and provider fallback

The provider used for an evaluation is chosen like this:

1. `DEMO_MODE=true`: always the demo provider (reason "DEMO_MODE is enabled"). The `.env` in this workspace currently sets `DEMO_MODE=true`, so demo runs are forced even if keys are present. Set it to `false` to use real providers.
2. Otherwise, the requested provider is used if its API key is set.
3. If its key is missing, the evaluation falls back to the demo provider and records the reason, for example "OPENAI_API_KEY is not configured".

The fallback is never silent. The evaluation stores `ai_config.requested_provider` and `ai_config.fallback_reason`, the response carries `is_demo: true`, and the UI shows a demo banner. If a real provider fails during a run (HTTP error, timeout), the evaluation is marked `failed` with a sanitized message. It does not switch to demo partway through.

The demo provider is deterministic and needs no network:

- For generated code, it picks one of 17 curated vulnerable samples by language and task keywords (Python SQLi, command injection, path traversal, deserialization, weak crypto, secrets; JavaScript XSS, SQLi, command injection, secrets/crypto, path traversal; plus Java, C, C++, C#, PHP and Rust). Each round it returns the next, more secure stage.
- For your own code, it applies rule-specific fixers (for example md5 → sha256, `shell=True` → `shell=False`, `pickle` → `json`, `innerHTML` → `textContent`, hardcoded secret → environment variable). It fixes one severity tier per round. It cannot repair SQL injection, path traversal or JavaScript command injection in arbitrary code and says so ("configure a real AI provider").
- Token counts for demo runs are estimates (`len(code) // 4`).

## Security scanners

| Scanner | Languages | Notes |
|---------|-----------|-------|
| Built-in rule engine | python, javascript, java, c, cpp, csharp, php, rust | About 24 regex rules with file-level suppression (for example, path traversal is suppressed when a containment check is present). Each finding has the CWE, severity, confidence, line, snippet, why it is vulnerable and how to fix it. |
| Bandit 1.7.6 | python | Runs as a `python -m bandit -f json` subprocess on a temporary file that is always deleted. Findings on the same line with the same CWE as a built-in finding are merged into it (`corroborated_by: ["bandit:B608"]`). Errors or timeouts are reported in `errors` and never crash a run. |
| Semgrep | – | Not integrated (no Windows binary; registry rules need network). Health reports `semgrep: "not_integrated"`. |

Covered CWEs include CWE-89 (SQL injection), CWE-78 (OS command injection), CWE-22 (path traversal), CWE-502 (deserialization), CWE-327 (weak crypto), CWE-798 (hardcoded credentials), CWE-95 (eval injection), CWE-79 (XSS) and CWE-120 (buffer overflow).

Known limitation: built-in rules match one line at a time. SQL text in a multi-line string or template literal that is concatenated or interpolated on a different line is not detected for JavaScript, Java, C#, PHP, Rust, C and C++. Python is covered by Bandit B608, which parses the whole statement.

Security label per version: `1 = insecure` if any finding is CRITICAL, HIGH or MEDIUM. LOW findings are shown but do not change the label. The reflexion loop stops early (`stopped_early: true`) when a version has zero findings. It also stops when a version is labelled secure and the provider returned the previous code unchanged, which only happens when LOW findings remain.

## Metrics

Labels: `y = 1` insecure, `y = 0` secure. All rates compare version `t` with the baseline `t0`:

```
Repair@t     = #(y0 = 1 and yt = 0) / #(y0 = 1) × 100
Regression@t = #(y0 = 0 and yt = 1) / #(y0 = 0) × 100
NetGain@t    = Repair@t − Regression@t
```

- When a denominator is zero, the rate is reported as `0.0` with `repair_defined: false` / `regression_defined: false`. The UI shows "n/a".
- Per evaluation N = 1. The dashboard aggregates over all completed evaluations. An evaluation that stopped early carries its last label forward to later rounds.
- Secure rate = the percentage of versions labelled secure (baseline vs final).

Implementation: `backend/app/services/metrics_service.py`, unit-tested in `backend/tests/test_metrics.py`.

## API

All endpoints are JSON under `/api`. Full schemas are at `/docs`.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Status, version, DB type, provider and scanner availability |
| GET | `/api/settings` | Read-only settings: providers (live / demo-fallback / demo-forced), scanners, languages, round limits |
| GET | `/api/samples?language=` | Curated vulnerable examples |
| POST | `/api/scan` | Scan `{code, language}` without storing anything |
| POST | `/api/evaluations` | Start an evaluation (201, status `pending`) |
| GET | `/api/evaluations?page&page_size&status&language` | Paginated list |
| GET | `/api/evaluations/{id}` | Detail: versions, findings, diffs, explanations, metrics |
| GET | `/api/evaluations/{id}/code/{version}` | A single version (`t0`, `t1`, …) |
| POST | `/api/evaluations/{id}/cancel` | Cancel a pending or running evaluation (409 if already finished) |
| DELETE | `/api/evaluations/{id}` | Delete an evaluation and its data |
| GET | `/api/analytics/dashboard` | KPIs, reflexion curve, severity and CWE breakdowns, recent runs |
| GET | `/api/analytics/by-language` | Secure rates per language |
| GET | `/api/analytics/by-cwe` | Found / fixed / remaining per CWE |

Example:

```bash
curl -X POST http://127.0.0.1:8000/api/evaluations \
  -H "Content-Type: application/json" \
  -d '{"task":"Look up a user by username in SQLite","language":"python","ai_provider":"demo","reflexion_rounds":3}'
```

Request body fields: `task` (3..5000 chars), `language` (`python`, `javascript`, `java`, `c`, `cpp`, `csharp`, `php`, `rust`), `ai_provider` (`demo`, `openai`, `anthropic`, `google`), optional `ai_model`, `reflexion_rounds` (1..10, default 3), optional `code` (start from your own code instead of generating t0), and optional `ai_config` (up to 20 scalar keys).

Errors: `{"detail": "..."}`. Validation errors return 422 `{"detail": "Validation failed", "errors": [{"field": "body.reflexion_rounds", "message": "..."}]}` and do not echo your input. Unhandled errors return 500 `{"detail": "Internal server error", "request_id": "..."}`. Every response has an `X-Request-ID` header.

## Tests

```powershell
cd backend
.\venv\Scripts\python.exe -m pytest -q
```

The suite covers metrics, every scanner rule (positive and negative), Bandit merge/dedupe, demo samples, the HTTP providers (via `httpx.MockTransport`, no network), the reflexion engine and the API end to end. Tests use a temporary SQLite database and blank API keys.

Frontend checks:

```powershell
cd frontend
npm run type-check
npm run build
```

## Docker

```bash
docker compose up --build                       # backend (SQLite in the backend_data volume) + frontend
docker compose --profile postgres up --build    # also starts PostgreSQL 15
```

- Ports are published on `127.0.0.1` only (`3000` frontend, `8000` backend for `/docs`, `5432` with the postgres profile). The frontend reaches the backend over the compose network at `backend:8000`.
- `backend`: `python:3.11-slim`, runs as a non-root user, database at `/app/data/securereflex.db` in the `backend_data` volume, healthcheck on `/api/health`. It reads `.env` for API keys and `DEMO_MODE`. Compose sets `ENVIRONMENT=production`, `DATABASE_URL` and `CORS_ORIGINS`.
- `frontend`: multi-stage `node:20-alpine` build. `BACKEND_URL=http://backend:8000` is a build argument because Next.js fixes rewrites at build time.
- To use PostgreSQL, start with `--profile postgres` and change the backend `DATABASE_URL` to `postgresql+asyncpg://postgres:postgres@postgres:5432/securereflex` (see the comment in `docker-compose.yml`). The schema is created at startup with `create_all`. Alembic is not run.

## Security notes

- **The API has no authentication and no rate limiting.** Anyone who can reach port 8000 (or 3000, through the proxy) can create, read and delete evaluations. Run it on localhost or a trusted network only, and do not expose it to the internet as is.
- API keys are read only from the environment / `.env`. They are never returned by the API or written to logs. Provider logs contain only provider, model, status code and latency. Prompts and code are not logged.
- Provider errors are sanitized (no response bodies or keys). Validation errors do not echo input.
- CORS is restricted to `CORS_ORIGINS` (no credentials). Origin `null` is rejected unless `ALLOW_NULL_ORIGIN=true`. Responses carry `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` and `Referrer-Policy: no-referrer`.
- Submitted code is stored in the database and is only scanned, never executed. Bandit analyses a temporary copy that is deleted afterwards.
- `GET /api/settings` is read-only. Settings cannot be changed at runtime.

## Next steps

- Authentication and authorization (JWT, RBAC)
- Rate limiting and request quotas
- A Redis/Celery job queue instead of in-process background tasks
- Alembic migrations (the schema is currently created with `create_all`)
- Semgrep integration (Linux/Docker) for broader rule coverage
- Multi-tenant data isolation
- Benchmark datasets for larger-scale Repair@t / Regression@t studies

## License and attribution

Research reference: "Secure Code Generation at Scale with Reflexion", arXiv:2511.03898. Fonts in `frontend/public/fonts` are distributed under the licenses in `frontend/public/fonts/LICENSES.txt`.
