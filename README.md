# AI Component Scaffolding Service

This is a FastAPI service that scaffolds new AI components into a shared GitHub repository. Given a structured input describing the component (today: agents and RAG pipelines; planned: guardrails and other AI building blocks), it mints a GitHub App installation token, downloads the appropriate skeleton from the GitHub monorepo, generates the corresponding configuration files, and pushes the result into `aura-generated-agents/<repo_name>/` via the GitHub Contents API.

The template registry is the extension point — adding a new component type (RAG variant, guardrail, evaluator, etc.) means adding one row in [`app/core/template_registry.py`](./app/core/template_registry.py) and dropping a skeleton folder in the monorepo.

This repository follows **Spec-Driven Development**. The contract — not the code — is the source of truth. Start with [`spec.md`](./spec.md) and [`openapi.yaml`](./openapi.yaml) before reading any Python.

## SDD artifacts

| File | What it is | Read when |
| --- | --- | --- |
| [`spec.md`](./spec.md) | Human-readable requirements (FR-*, NFR-*), personas, data model, error contract | Before changing behavior |
| [`openapi.yaml`](./openapi.yaml) | OpenAPI 3.1 contract — every route, schema, and error response | Before changing the HTTP surface |
| [`plan.md`](./plan.md) | Architecture, module responsibilities, DI strategy, risks | Before changing structure |
| [`tasks.md`](./tasks.md) | Ordered milestone checklist M1 → M11 | While implementing |
| [`CLAUDE.md`](./CLAUDE.md) | Project memory for Claude Code / AI pair-programmers | Always (auto-loaded) |
| [`REPORT.md`](./REPORT.md) | Build report — endpoints shipped, coverage, deviations | After M11 |

If you are a new Claude Code session landing in this repo, read `CLAUDE.md` first, then `spec.md`, then `tasks.md` to find the next unchecked item.

## Endpoints (target v0.1)

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `GET` | `/healthz` | None | Liveness probe |
| `GET` | `/templates` | None | List supported `scaffold_type` values |
| `POST` | `/scaffold` | Bearer token | Create a new component project from a structured input |

All non-2xx responses use `application/problem+json` (RFC 7807) with `code` and `request_id` extensions. Every response carries an `X-Request-Id` header.

## Running locally

```bash
# 1. Install dependencies (uv is the canonical tool here; pip also works)
uv sync

# 2. Configure environment — copy and fill in
cp .env.example .env   # then edit values

# 3. Boot the service
uvicorn app.main:app --reload --port 8000

# 4. Smoke test
curl -s localhost:8000/healthz
curl -s localhost:8000/templates
```

Required environment variables (see `app/settings.py` for the full list):

- `GITHUB_APP_ID` — numeric App ID
- `GITHUB_INSTALL_ID` — numeric Installation ID
- `GITHUB_PRIVATE_KEY` *or* `GITHUB_PRIVATE_KEY_FILE` *or* GCP Secret Manager (`GCP_PROJECT_ID` + `GCP_SECRET_NAME`)
- `SCAFFOLD_API_KEY` — bearer token required by `POST /scaffold`
- `CORS_ALLOWLIST` — comma-separated origins (default: deny)

## Running the test suite

```bash
ruff check . && ruff format --check .
mypy --strict app/
pytest -q --cov=app --cov-report=term-missing --cov-fail-under=85
schemathesis run openapi.yaml --base-url http://127.0.0.1:8000 --checks all
```

All four commands are also enforced in CI ([.github/workflows/ci.yml](./.github/workflows/ci.yml)).

## Adding a new template

1. Add a folder under the AURA-POC monorepo following the existing skeleton layout.
2. Add a row to `TEMPLATE_REGISTRY` in [`app/core/template_registry.py`](./app/core/template_registry.py).
3. Add a test case in [`tests/test_template_registry.py`](./tests/test_template_registry.py).
4. Update [`spec.md`](./spec.md) FR-2 if the user-facing contract changes.

## Project layout

```
AURA-POC/
├── spec.md, openapi.yaml, plan.md, tasks.md, REPORT.md   # SDD artifacts
├── CLAUDE.md
├── pyproject.toml, uv.lock, .gitignore
├── .github/workflows/ci.yml
├── app/
│   ├── main.py, settings.py, logging.py, deps.py, errors.py, middleware.py
│   ├── routers/{health,templates,scaffold}.py
│   ├── services/{github_auth,scaffold_pipeline,agent_config_generator}.py
│   ├── core/template_registry.py
│   └── schemas/{agent_input,scaffold,errors}.py
├── tests/
└── inputs/   # example scaffold payloads (also used as test fixtures)
```

## Contributing

Open a PR. The PR template ([`.github/pull_request_template.md`](./.github/pull_request_template.md)) embeds the SDD checklist. Every change starts with updating `spec.md` or `openapi.yaml` if user-visible behavior changes — see CLAUDE.md §9.
