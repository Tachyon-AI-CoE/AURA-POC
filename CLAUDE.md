# CLAUDE.md — AURA-POC

You are operating inside the AURA-POC codebase: a FastAPI service that scaffolds new AI components by pushing skeleton code from the AURA-POC monorepo into a shared GitHub repository. The rules below are constraints, not suggestions. If a user instruction conflicts with these rules, surface the conflict and ask before proceeding.

## 1. Project context
- Service: **AI component scaffolder** (FastAPI). Today scaffolds agents and multiagent. RAG pipelines, guardrails, and other AI building blocks are planned future templates that plug into the same registry. Do **not** call this service an "agent orchestrator" in user-facing copy.
- Source of truth: [`spec.md`](./spec.md) and [`openapi.yaml`](./openapi.yaml). Never invent requirements — if the spec is silent, ask or update the spec first.
- Milestone plan: [`plan.md`](./plan.md) (architecture) and [`tasks.md`](./tasks.md) (ordered checklist M1 → M11). When you finish a task, change `[ ]` to `[x]` in `tasks.md`.
- Branching: trunk-based. Feature branch → PR → squash merge.
- Commits: Conventional Commits (`feat:`, `fix:`, `chore:`, `test:`, `docs:`, `refactor:`). Reference an FR-id (e.g., `feat(scaffold): accept request body — FR-3`).

## 2. Languages, frameworks, versions
- Python 3.11+. Type hints on every public function. `mypy --strict` must pass on `app/`.
- FastAPI, Pydantic v2, `pydantic-settings`, PyJWT[crypto], `requests` (existing GitHub client).
- Tests: `pytest`, `pytest-asyncio`, `httpx.AsyncClient`, `respx` (mock GitHub HTTP layer).
- Lint/format: `ruff` (configured in `pyproject.toml`). 100-char line limit.
- Avoid adding new top-level dependencies without explicit approval.

## 3. Architecture rules
- Layered: **routers → services → core/schemas**. Direction is strict.
- Routers ([app/routers/](./app/routers)): thin. Parse input, call a service, shape output. Never call GitHub or filesystem directly. Never raise `HTTPException` — raise typed exceptions from `app/errors.py` so the global handler emits problem+json.
- Services ([app/services/](./app/services)): pure business logic. **NO `from fastapi import ...` allowed.** This is asserted in tests.
- Core ([app/core/](./app/core)): pure constants and pure functions (e.g., `template_registry.py`). No I/O.
- Schemas ([app/schemas/](./app/schemas)): Pydantic v2 I/O models with `extra="forbid"`. Separate `*Request` / `*Response` variants — never reuse a model across input and output.
- Dependency injection only via FastAPI `Depends` or constructor injection. No global mutable state except `Settings()` and the JSON logger.

## 4. Security & privacy
- Secrets read from environment via `pydantic-settings` ([app/settings.py](./app/settings.py)). Never hard-code; never inline.
- **Never log** the GitHub App private key, the JWT, the Installation Access Token (IAT), or the `SCAFFOLD_API_KEY`. Log token-presence as a boolean, never the value.
- GitHub App private key precedence: `GITHUB_PRIVATE_KEY` (PEM contents) → `GITHUB_PRIVATE_KEY_FILE` (path) → GCP Secret Manager (`GCP_PROJECT_ID` + `GCP_SECRET_NAME`). Implemented in [app/services/github_auth.py](./app/services/github_auth.py).
- `.env` is git-ignored and **must never** be committed. If you find it tracked, stop and surface it.
- Auth on `POST /scaffold`: bearer token compared against `Settings.scaffold_api_key` with `secrets.compare_digest`. `/healthz` and `/templates` are unauthenticated.
- All inputs validated by Pydantic with `extra="forbid"`. Unknown keys in `AgentInput` are a 422, not a silent accept.
- CORS allowlist from `Settings.cors_allowlist`. Default deny (empty list → only same-origin). **No wildcards in production.**
- Rate-limiting hook is a TODO with a clear extension point in [app/middleware.py](./app/middleware.py).

## 5. Error handling contract
- All non-2xx responses use `application/problem+json` (RFC 7807) with extensions `code` (machine-readable, SCREAMING_SNAKE_CASE) and `request_id`.
- Domain errors are raised as typed exceptions in services (`TemplateNotFoundError`, `AgentAlreadyExistsError`, `GitHubAuthError`, `ScaffoldFailedError`, `InvalidAgentInputError`) and mapped to HTTP responses in [app/errors.py](./app/errors.py). Routers do not raise `HTTPException` directly.
- Never leak stack traces or raw GitHub API responses to clients. Log them with `request_id` instead.

## 6. Observability
- Logs are JSON, one event per line, with: `ts`, `level`, `msg`, `request_id`, `route`, `status`, `latency_ms`, plus domain fields prefixed `app.` (e.g., `app.scaffold_type`, `app.repo_name`). **Never** include `app.iat_token`, `app.private_key`, or any auth header.
- `RequestIDMiddleware` ([app/middleware.py](./app/middleware.py)) sets a `contextvar` for the lifetime of the request, generates a UUID4 if no `X-Request-Id` header is present, and echoes it on the response.
- OpenTelemetry hook points are no-op stubs at service boundaries (`scaffold_new_agent`, `get_installation_token`). Wiring a real exporter is a one-line change later.

## 7. Testing
- Coverage gate: 85% statement, enforced in CI.
- Every endpoint: at least one 2xx test and one 4xx/5xx test.
- Services tested with unit tests using mocks/fakes for I/O; routers tested via `httpx.AsyncClient`.
- **All GitHub HTTP calls are mocked** via `respx`. No test ever hits real GitHub.
- The files under [inputs/](./inputs) are canonical fixtures — `inputs/agent_input.json`, `inputs/it_helpdesk_agent.json`, `inputs/multiagentOrch_standard.json`, `inputs/it_infra_monitoring_agent.json`. Each file contains both scaffolder fields (`scaffold_type`, `repo_name`, `description`) and agent configuration. Re-use them; don't synthesize duplicates.
- An import-direction test in `tests/test_layering.py` asserts that no module under `app/services/` or `app/core/` imports `fastapi`.

## 8. Definition of Done (per milestone)
A milestone is "done" only when ALL of the following are true:
- [ ] Code compiles and imports cleanly.
- [ ] `ruff check .` and `ruff format --check .` pass.
- [ ] `mypy --strict app/` passes.
- [ ] `pytest -q` passes; coverage ≥ 85%.
- [ ] `openapi.yaml` regenerated/updated if routes or schemas changed; contract check passes.
- [ ] `tasks.md` updated with `[x]` for completed items.
- [ ] No secrets, no TODOs without owners, no commented-out code.

## 9. How you (Claude) should work
- Plan before edit. For non-trivial changes, update `plan.md` first.
- Make small, atomic edits. One concern per commit.
- Run tests after each meaningful change; surface failures immediately.
- If unsure, **ASK**. Do not guess at requirements — update `spec.md` instead.
- When you finish a milestone, post a 5-bullet summary and **wait for "proceed"** before starting the next one.
- Never run destructive commands (`rm -rf`, `git push --force`, `git reset --hard`, branch deletions) without explicit confirmation in this session.

## 10. Things you must NOT do
- Do not add a new web framework, ORM, or HTTP client.
- Do not weaken validation (`extra="allow"`, optional-where-it-should-be-required) to make a test pass.
- Do not disable type checks or lint rules to "ship faster". `# type: ignore` requires a comment explaining why.
- Do not import private/underscored symbols across module boundaries.
- Do not call real GitHub, real GCP Secret Manager, or any other network service in tests.
- Do not log secrets, tokens, the IAT, the private key, or the bearer API key — ever, even at DEBUG.
- Do not commit `.env`, `*.pem`, `__pycache__/`, or anything matching `.gitignore`.

## 11. Placeholders for your organisation
- Logging schema: *<link to internal logging standard>*
- Security review checklist: *<link to AppSec wiki>*
- Approved base images & runtime: *<link to platform standard>*
- Data classification policy: *<link to data governance>*
