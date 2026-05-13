# AURA-POC — Implementation Plan (v0.1)

This plan derives from [`spec.md`](./spec.md) and feeds [`tasks.md`](./tasks.md). It is read alongside [`CLAUDE.md`](./CLAUDE.md) (project memory). The plan describes **structure**; the spec describes **behavior**; tasks describe **order of work**.

## 1. Final folder layout

```
AURA-POC/
├── spec.md, openapi.yaml, plan.md, tasks.md, REPORT.md   # SDD artifacts
├── CLAUDE.md
├── README.md
├── pyproject.toml, uv.lock
├── .gitignore
├── .env.example                         # placeholder values, safe to commit
├── .github/
│   ├── workflows/ci.yml
│   └── pull_request_template.md
├── app/
│   ├── __init__.py
│   ├── main.py                          # FastAPI app factory + middleware wiring
│   ├── settings.py                      # pydantic-settings, env-driven
│   ├── logging.py                       # JSON logger + request_id contextvar
│   ├── deps.py                          # auth + settings DI providers
│   ├── errors.py                        # typed domain exceptions + problem+json handlers
│   ├── middleware.py                    # RequestIDMiddleware
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── health.py                    # GET /healthz                       (FR-1)
│   │   ├── templates.py                 # GET /templates                     (FR-2)
│   │   └── scaffold.py                  # POST /scaffold                     (FR-3..FR-11)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── github_auth.py               # JWT mint + IAT cache               (FR-13)
│   │   ├── scaffold_pipeline.py         # full scaffold pipeline             (FR-8)
│   │   └── agent_config_generator.py    # JSON → YAML transform              (FR-8)
│   ├── core/
│   │   ├── __init__.py
│   │   └── template_registry.py         # pure constants + lookup
│   └── schemas/
│       ├── __init__.py
│       ├── agent_input.py               # RootAgent, SubAgent, GenerateContentConfig, AgentInput
│       ├── scaffold.py                  # ScaffoldRequest, ScaffoldResponse
│       └── errors.py                    # Problem (RFC 7807)
├── tests/
│   ├── conftest.py
│   ├── test_health.py
│   ├── test_templates.py
│   ├── test_scaffold.py                 # integration with mocked GitHub
│   ├── test_agent_config_generator.py
│   ├── test_template_registry.py
│   ├── test_github_auth.py
│   ├── test_errors.py
│   └── test_layering.py                 # asserts services/* do not import fastapi
└── inputs/                              # canonical example payloads (also fixtures)
    ├── agent_input.json
    ├── it_helpdesk_agent.json
    └── multiagentOrch_standard.json
```

## 2. Module responsibilities

| Module | Responsibility | May import |
| --- | --- | --- |
| `app/routers/*` | Thin HTTP layer. Parse input, call a service, shape output. | `fastapi`, `app.schemas`, `app.services`, `app.deps`, `app.errors` |
| `app/services/*` | Pure business logic (GitHub auth, scaffold pipeline, JSON→YAML transform). **No FastAPI imports.** Raise typed exceptions from `app.errors`. | `app.schemas`, `app.core`, `app.errors`, stdlib, `requests`, `PyJWT`, `PyYAML` |
| `app/core/*` | Pure constants and pure functions. No I/O. | stdlib only |
| `app/schemas/*` | Pydantic v2 I/O models with `extra="forbid"`. Separate Request/Response variants. | `pydantic` only |
| `app/errors.py` | Typed domain exceptions and the FastAPI exception handlers that emit problem+json. | `fastapi`, `pydantic`, `app.schemas.errors` |
| `app/middleware.py` | `RequestIDMiddleware` (ULID generator, contextvar binding, `X-Request-Id` echo); per-request log line on response. | `fastapi`, `starlette`, `app.logging` |
| `app/settings.py` | `Settings(BaseSettings)` — single source for all env-driven config. | `pydantic_settings`, `pydantic` |
| `app/logging.py` | JSON logger factory + `request_id` contextvar. | stdlib (`logging`, `contextvars`, `json`) |
| `app/deps.py` | DI providers: `get_settings`, `require_api_key`. | `fastapi`, `app.settings`, `app.errors` |
| `app/main.py` | `create_app()` factory: instantiate FastAPI, register middleware, mount routers, register exception handlers. | everything in `app/` |

## 3. Dependency-injection strategy

- `Settings()` is constructed once at app startup and provided via `Depends(get_settings)`. Tests override with `app.dependency_overrides[get_settings] = ...`.
- `require_api_key(settings: Settings = Depends(get_settings), authorization: str = Header(...))` — applied to `POST /scaffold`. Constant-time compare with `secrets.compare_digest`. Returns a `Principal` placeholder for future role expansion.
- GitHub services are plain classes constructed inside routers via `Depends`, taking `Settings` in their constructor. No service-level singletons except the IAT cache lives as a module-level guarded dict (existing behavior preserved from [github_app.py:32-35](./github_app.py#L32-L35)).
- Test profile: `pytest` fixture injects a `Settings(scaffold_api_key="test", cors_allowlist=["http://testserver"], ...)` and overrides `get_settings`.

## 4. Test strategy

| Layer | Tooling | What it covers |
| --- | --- | --- |
| Unit (services) | `pytest`, mocks via `respx` for GitHub HTTP, in-memory inputs | `agent_config_generator.generate_agent_config`, `github_auth.get_installation_token` (JWT claims, cache hit/miss, refresh), `template_registry.get_template_repo`, `scaffold_pipeline.scaffold_new_agent` decomposed steps |
| Integration (routers) | `httpx.AsyncClient` against the FastAPI app with overridden deps; GitHub fully mocked via `respx` | `/healthz`, `/templates`, `/scaffold` happy + each error path. Each negative test asserts the problem+json shape and the `request_id` field. |
| Contract | `schemathesis run openapi.yaml --base-url http://127.0.0.1:8000 --checks all` | Drift check between handlers and `openapi.yaml`. Runs in CI after a uvicorn boot. |
| Layering | `tests/test_layering.py` (AST walk) | Asserts no `app.services.*` or `app.core.*` module contains `import fastapi` or `from fastapi`. |

Coverage gate: 85% statement, enforced with `pytest --cov-fail-under=85`. The three files under [inputs/](./inputs) double as fixtures — re-used; not synthesized again.

## 5. Observability

- **JSON logs**, one event per line, fields: `ts`, `level`, `msg`, `request_id`, `route`, `status`, `latency_ms`, plus `app.*` domain fields. Never emit secrets, tokens, the IAT, or the private key.
- **Request id**: `RequestIDMiddleware` echoes inbound `X-Request-Id` or generates a ULID; binds it to a `contextvar` consumed by the log filter; adds it to every response header. (FR-10)
- **Per-request log line**: emitted in the middleware on response, after the handler completes, regardless of outcome.
- **OpenTelemetry**: no-op hook points at `scaffold_new_agent` and `get_installation_token` boundaries — a real exporter is one line to add later.
- **Metrics**: no exporter in v0.1; structured logs are the primary signal. A `/metrics` endpoint and Prometheus client are listed as v0.2.

## 6. Risks & mitigations

| ID | Risk | Mitigation in v0.1 | v0.2 follow-up |
| --- | --- | --- | --- |
| R1 | **File-by-file Contents API push leaves orphaned subfolders on failure.** Mid-flight network error → partial push. | Existence check before push (FR-6). Failure path logs the partial state with `request_id`. | Switch to Git Trees + Commit API for atomic push. |
| R2 | **Race on the existence check.** Two concurrent scaffolds for the same `repo_name` both pass and corrupt each other. | Documented limitation. Single-instance deploy mitigates risk in v0.1. | Short-lived distributed lock keyed on `repo_name`, or a unique-name index. |
| R3 | **Private-key leakage via logs.** Raw exceptions from PyJWT can include key material. | All exception handlers in `errors.py` whitelist what reaches the client. CLAUDE.md §4 enforces the rule. Test `test_github_auth.py` asserts no key material in log output. | None — this stays. |
| R4 | **IAT expiry mid-push.** A scaffold that runs longer than the IAT's residual lifetime fails halfway through. | 5-minute refresh window already in [github_app.py:153-155](./github_app.py#L153-L155); preserved. | Mid-flight token refresh hook in the Contents API loop. |
| R5 | **Spec/code drift.** Schema changes in code without OpenAPI update. | `schemathesis` contract check in CI fails the build on drift. | None — this stays. |
| R6 | **Test/prod divergence via over-mocking.** GitHub mocks pass but real API doesn't. | A separate (manual, optional) smoke target hits a sandbox repo. Not a PR gate to avoid burning tokens. | Scheduled nightly smoke against a sandbox org. |
| R7 | **`.env` already tracked.** `git rm --cached .env` only affects current commit, not history. | M1 stops tracking; `REPORT.md` flags any historical leak and recommends rotation + history rewrite. | Out of scope for AURA — owned by AppSec. |

## 7. What stays vs. what changes

| File / behavior | Status |
| --- | --- |
| `inputs/*.json` schema | **Unchanged** — these are the canonical examples and they remain valid. |
| GitHub App auth flow (JWT → IAT, 9-min JWT, 5-min refresh, key precedence) | **Preserved verbatim** — moved into `app/services/github_auth.py`. |
| `scaffold_new_agent()` pipeline | **Preserved** — moved into `app/services/scaffold_pipeline.py`. The file-by-file push is unchanged in v0.1; atomic push is a v0.2 risk-mitigation. |
| `agent_config_generator.generate_agent_config()` + `_ADKDumper` | **Preserved verbatim** — moved into `app/services/agent_config_generator.py`. |
| `TEMPLATE_REGISTRY` | **Preserved values** — moved into `app/core/template_registry.py`. `rag_pipeline` stays registered but is documented as future / not-yet-production. |
| `POST /scaffold` input source | **Changed** — accepts request body (FR-3). File path (`AGENT_INPUT_PATH`) is a fallback (FR-11). |
| Auth on `POST /scaffold` | **Added** — bearer token (FR-4). |
| CORS | **Changed** — wildcard removed; allowlist from settings (NFR-8). |
| Error contract | **Changed** — problem+json with `code` and `request_id` (FR-9). |
| Logging | **Changed** — JSON, structured, `request_id`-carrying (FR-12). |
