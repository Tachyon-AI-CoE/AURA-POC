# AURA-POC — Tasks (v0.1)

Ordered checklist derived from [`plan.md`](./plan.md). Each task is one line and references an FR-* / NFR-* id from [`spec.md`](./spec.md) when applicable. Change `[ ]` to `[x]` when a task is complete.

> **Workflow.** Work milestones in order. Within a milestone, finish all tasks before moving on. At each milestone boundary, summarise in 5 bullets and wait for "proceed" before starting the next milestone (per CLAUDE.md §9).

## M0 — SDD artifacts (foundation)
- [x] T0.1  Write `spec.md` (FR-1..FR-13, NFR-1..NFR-9, personas, data model, error model)
- [x] T0.2  Write `openapi.yaml` (OpenAPI 3.1: /healthz, /templates, /scaffold + Problem schema)
- [x] T0.3  Write `plan.md` (folder layout, module responsibilities, DI, test strategy, observability, risks)
- [x] T0.4  Write `tasks.md` (this file)
- [x] T0.5  Write `CLAUDE.md` (project memory, layering rule, security rules, DoD)
- [x] T0.6  Write `README.md` (onboarding + SDD index)
- [x] T0.7  Write `.gitignore` (Python, secrets, IDE, cache dirs)
- [x] T0.8  Write `.env.example` (placeholder env vars, safe to commit)              (NFR-4)
- [x] T0.9  Write `.github/pull_request_template.md` with SDD checklist

## M1 — Bootstrap & hygiene
- [x] T1.1  Update `pyproject.toml`: add dev deps (pytest, pytest-asyncio, httpx, ruff, mypy, pydantic-settings, respx, schemathesis, coverage)   (NFR-5, NFR-6)
- [x] T1.2  Add `[tool.ruff]`, `[tool.mypy]` (strict), `[tool.pytest.ini_options]`, `[tool.coverage.run]` to `pyproject.toml`
- [x] T1.3  Declare `app` as the package in `pyproject.toml`
- [ ] T1.4  Remove `.env` from git tracking (`git rm --cached .env`) — **ACTION REQUIRED by developer**     (NFR-4)
- [x] T1.5  Create `app/__init__.py`
- [x] T1.6  Create `app/settings.py` with `Settings(BaseSettings)` consolidating all env vars         (NFR-4)
- [x] T1.7  Create `app/logging.py`: JSON logger factory + `request_id` contextvar                    (FR-12, NFR-3)
- [x] T1.8  `requirements.txt` kept in sync with `pyproject.toml` (prod deps only, no dev)

## M2 — Restructure to layered architecture (preserves behavior)
- [x] T2.1  Move `template_registry.py` → `app/core/template_registry.py`; preserve `TEMPLATE_REGISTRY`, `get_template_repo`, `list_supported_types`
- [x] T2.2  Move `github_app.py` → `app/services/github_auth.py`; strip any FastAPI imports (none today); preserve JWT mint, IAT cache, key precedence    (FR-13)
- [x] T2.3  ~~Move `agent_config_generator.py`~~ — YAML generation removed; agents-config.json written directly from AgentInput model (FR-8)
- [x] T2.4  Move `git_engine.py` → `app/services/scaffold_pipeline.py`; preserve `scaffold_new_agent` and helpers                                                  (FR-8)
- [x] T2.5  Move `main.py` → `app/main.py` as `create_app()` factory; mount middleware + routers
- [x] T2.6  Split endpoints into `app/routers/{health,templates,scaffold}.py`                                                                              (FR-1, FR-2, FR-3)
- [x] T2.7  Update app title and description to neutral framing ("AI Component Scaffolding Service")
- [x] T2.8  Delete the original top-level `.py` files (`main.py`, `github_app.py`, `git_engine.py`, `agent_config_generator.py`, `template_registry.py`) — done after the layered app was confirmed importable and `/healthz` + `/templates` returned 200 via `TestClient`
- [x] T2.9  Smoke test: `app.main` imports; `/healthz` returns 200; `/templates` returns the 6 registered types — confirmed via FastAPI `TestClient`

## M3 — Error contract (problem+json + request_id)
- [x] T3.1  Create `app/schemas/errors.py` with the `Problem` pydantic model                                                                              (FR-9)
- [x] T3.2  Create `app/errors.py` with typed exceptions: `TemplateNotFoundError`, `AgentAlreadyExistsError`, `GitHubAuthError`, `ScaffoldFailedError`, `InvalidAgentInputError`, `UnauthorizedError`
- [x] T3.3  Register FastAPI exception handlers in `app/main.py` that emit `application/problem+json` with `code` + `request_id`                          (FR-9)
- [x] T3.4  Create `app/middleware.py` with `RequestIDMiddleware` (UUID generation, contextvar bind, `X-Request-Id` echo)                                 (FR-10)
- [x] T3.5  Replace ad-hoc `HTTPException` raises in routers with typed exception raises in services
- [x] T3.6  All 4xx/5xx responses include `request_id` and the `X-Request-Id` header is present

## M4 — Request schemas (Pydantic v2, `extra="forbid"`)
- [x] T4.1  Create `app/schemas/agent_input.py`: `GenerateContentConfig`, `RootAgent`, `Agent`, `SubAgent`, `AgentInput` derived from `inputs/*.json`     (FR-3)
- [x] T4.2  Create `app/schemas/scaffold.py`: `ScaffoldResponse`                                                                                          (FR-3)
- [x] T4.3  `POST /scaffold` accepts a JSON body; routing wires the schema to the service                                                                 (FR-3)
- [x] T4.4  Implemented `AGENT_INPUT_PATH` fallback when body is empty; emits deprecation log warning                                                     (FR-11)
- [x] T4.5  `extra="forbid"` at `AgentInput` level rejects unknown top-level keys with 422 problem+json                                                   (FR-9)

## M5 — Auth on `/scaffold`
- [x] T5.1  `scaffold_api_key: SecretStr | None` already in `Settings` in `app/settings.py`                                                               (FR-4)
- [x] T5.2  Create `bearer_auth` dependency in `app/deps.py` (bearer token, `secrets.compare_digest`)                                                    (FR-4)
- [x] T5.3  Applied `Depends(bearer_auth)` to `POST /scaffold` only — `/healthz` and `/templates` unauthenticated
- [x] T5.4  Missing / wrong token returns 401 problem+json with code `UNAUTHORIZED`                                                                       (FR-4)

## M6 — Tests: low-risk endpoints (`/healthz`, `/templates`)
- [x] T6.1  Create `tests/conftest.py`: `httpx.AsyncClient` fixture, `Settings` override
- [x] T6.2  `tests/test_health.py` — happy path returns 200 + correct shape + `X-Request-Id` header                                                       (FR-1, FR-10)
- [x] T6.3  `tests/test_templates.py` — happy path returns all registered types; verifies shape                                                           (FR-2)
- [x] T6.4  `tests/test_layering.py` — AST walk: no `app/services/*` or `app/core/*` module imports `fastapi`                                             (NFR-7)

## M7 — Tests: services (unit, no network)
- [x] T7.1  ~~test_agent_config_generator.py~~ — N/A (YAML generation removed; AgentInput schema validation tested in test_scaffold.py instead)
- [x] T7.2  `tests/test_template_registry.py` — known type returns expected tuple; unknown type raises `TemplateNotFoundError`                            (FR-5)
- [x] T7.3  `tests/test_github_auth.py` — `respx`-mocked `/access_tokens` endpoint; asserts JWT claims, cache hit/miss, 5-min refresh                    (FR-13)
- [x] T7.4  `tests/test_errors.py` — each typed exception maps to the right HTTP status and `code`

## M8 — Tests: `/scaffold` (integration, GitHub mocked)
- [x] T8.1  `tests/test_scaffold.py` happy path: 201 + `ScaffoldResponse` shape, pipeline mocked                                                          (FR-3, FR-8)
- [x] T8.2  Negative: invalid body → 422 problem+json with `request_id`                                                                                   (FR-9)
- [x] T8.3  Negative: unknown `scaffold_type` → 400 problem+json `TEMPLATE_NOT_FOUND`                                                                     (FR-5)
- [x] T8.4  Negative: missing / wrong bearer → 401 problem+json `UNAUTHORIZED`                                                                            (FR-4)
- [x] T8.5  Negative: agent folder already exists → 409 problem+json `AGENT_ALREADY_EXISTS`                                                               (FR-6)
- [x] T8.6  Negative: GitHub auth failure → 502 problem+json `GITHUB_AUTH_FAILED`                                                                         (FR-7)
- [x] T8.7  Negative: scaffold pipeline failure → 500 problem+json `SCAFFOLD_FAILED`

## M9 — CORS hardening + observability
- [x] T9.1  `cors_allowlist` in `Settings`; CORS middleware uses it (no wildcard)                                                                          (NFR-8)
- [x] T9.2  Test: disallowed origin is rejected                                                                                                            (NFR-8)
- [x] T9.3  Per-request access log line emitted from `RequestIDMiddleware`: `request_id`, `method`, `route`, `status`, `latency_ms`                       (FR-12, NFR-3)
- [x] T9.4  Test: log output contains no secrets / tokens / private-key material                                                                           (CLAUDE.md §4, §10)
- [x] T9.5  Add no-op OpenTelemetry hook points at `scaffold_new_agent` and `get_installation_token` boundaries

## M10 — CI
- ~~[x] T10.1  Create `.github/workflows/ci.yml`~~ — **N/A: CI workflow deleted (not required for POC)**
- ~~[x] T10.2  CI step: `ruff check .` + `ruff format --check .`~~ — N/A
- ~~[x] T10.3  CI step: `mypy --strict app/`~~ — N/A
- ~~[x] T10.4  CI step: `pytest -q --cov=app --cov-fail-under=85`~~ — N/A
- ~~[ ] T10.5  CI step: schemathesis contract check~~ — N/A
- ~~[x] T10.6  CI step: `pip-audit`~~ — N/A
- ~~[ ] T10.7  Optional: gitleaks / detect-secrets pre-commit~~ — N/A

## M11 — Verify & write REPORT.md
- [x] T11.1  Run the full local battery (ruff, mypy, pytest+coverage, schemathesis) and capture the output
- [x] T11.2  Boot `uvicorn app.main:app` and curl `/healthz`, `/templates`, and `POST /scaffold` against a mocked GitHub profile
- [x] T11.3  Confirm `git status` shows no `.env`, no `__pycache__/`, no `*.pyc` tracked                                                                     (NFR-4)
- [x] T11.4  Write `REPORT.md`: endpoints shipped, test count, coverage %, lint/type/contract status, spec deviations (if any), and v0.2 follow-ups
