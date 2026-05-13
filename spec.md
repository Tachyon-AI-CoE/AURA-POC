# AURA-POC — Specification (v0.1)

> Status: **Aspirational v0.1** — describes the production target. Items currently implemented as of the pre-SDD code are noted inline; the gap is closed by the milestones in [`tasks.md`](./tasks.md).

## 1. Overview & business goals

AURA-POC is an **AI component scaffolding service**. It exposes a small HTTP API that, given a structured description of an AI component, creates a fully-formed project skeleton inside a shared GitHub repository and returns a pointer to it. Downstream automation (Cloud Build, CI) then picks up the new folder and continues the lifecycle.

**Today** AURA scaffolds two component families: **single agents** (`single_agent`, `single_agent_api`, `agent_clientapp`) and **multiagent** orchestrators / workflows (`multiagent_orchestrator`, `multiagent_workflow`). **Planned future templates** — registered or unregistered — include **RAG pipelines**, **guardrails**, and other AI building blocks. The template registry is the single extension point: a new component family ships as one entry in the registry plus one skeleton folder in the monorepo.

**Business goals.**
- Reduce time-to-first-commit for a new AI component from hours of manual copy-paste to a single API call.
- Enforce consistent project structure across every component the platform produces.
- Provide a single extension point so the platform team can ship a new component type by adding one row and one folder, with no service redeploy beyond a registry update.

**Non-goals (deliberately out of scope for v0.1).**
- Running the scaffolded component. AURA only creates the source; execution is handled by downstream Cloud Build / CI.
- Multi-tenant repository isolation. v0.1 assumes a single org and a single shared `aura-generated-agents` target repo.
- Full OAuth/OIDC for the API caller. v0.1 uses a static bearer token (`SCAFFOLD_API_KEY`).
- A web UI. The contract is the HTTP API.

## 2. Personas & permissions

| Persona | Identity | Reads `/templates` | Calls `/scaffold` | Notes |
| --- | --- | :---: | :---: | --- |
| `platform-admin` | Human operator with the bearer token | ✅ | ✅ | One token per environment; rotated per the org's secret policy |
| `pipeline-service` | CI/CD job invoking the API | ✅ | ✅ | Same bearer token mechanism; usage distinguished by `User-Agent` and log context only |
| `health-prober` | k8s liveness / load balancer | ✅ (`/healthz`) | ❌ | No auth needed |

There is intentionally no `customer` persona in v0.1 — AURA is an internal platform service.

## 3. Scope

### In scope (v0.1)
- Three endpoints: `GET /healthz`, `GET /templates`, `POST /scaffold`.
- GitHub App authentication (JWT → Installation Access Token) with in-memory IAT caching.
- problem+json error contract with `code` and `request_id` extensions.
- Structured JSON logging with a per-request correlation id.
- Static bearer-token auth on `POST /scaffold`.
- pytest suite ≥ 85% coverage; ruff and mypy strict in CI.
- **Working scaffold types:** `single_agent`, `single_agent_api`, `agent_clientapp`, `multiagent_orchestrator`, `multiagent_workflow`.
- **Registered but future / not yet production:** `rag_pipeline` (skeleton path exists in the registry but is a forward-looking entry; not advertised as ready in v0.1).

### Out of scope (v0.1, may revisit in v0.2)
- Production rollout of `rag_pipeline`, plus net-new templates for guardrails and other AI components. The registry shape is intentionally ready for these; the spec for each will be added when the corresponding skeleton is shipped.
- Atomic batch push (current implementation pushes files one-by-one — risk noted in `plan.md`).
- Retry/backoff on transient GitHub API failures.
- Rate limiting (hook point only — no enforcement).
- Real OAuth/OIDC, per-caller roles beyond a single shared token.
- Database persistence — every request is stateless aside from the in-memory IAT cache.
- Webhook receipt from GitHub (one-way push only).
- Concurrent scaffold execution safety (current existence check is not atomic).

## 4. Functional requirements

| ID | Requirement |
| --- | --- |
| **FR-1** | `GET /healthz` returns `200 OK` with `{"status": "ok", "version": <semver>, "timestamp": <ISO-8601 UTC>}`. Liveness only — does **not** check GitHub reachability. |
| **FR-2** | `GET /templates` returns the list of supported `scaffold_type` values, the source monorepo name, and a map of each type to its full skeleton path. Response is unauthenticated. Future / not-yet-production types may be flagged in a future minor revision. |
| **FR-3** | `POST /scaffold` accepts a JSON `ScaffoldRequest` body containing an `AgentInput` and returns `201 Created` with a `ScaffoldResponse` (`job_id`, `repo_url`, `config_path`, `template_used`, `created_at`, `message`). |
| **FR-4** | `POST /scaffold` requires a valid `Authorization: Bearer <token>` header matched against `SCAFFOLD_API_KEY` via constant-time compare. Missing / wrong token returns 401 problem+json with code `UNAUTHORIZED`. |
| **FR-5** | If `scaffold_type` is not in the template registry, the response is 400 problem+json with code `TEMPLATE_NOT_FOUND` and a `detail` listing the supported types. |
| **FR-6** | If the target subfolder (`aura-generated-agents/<repo_name>/`) already exists, the response is 409 problem+json with code `AGENT_ALREADY_EXISTS`. The existence check is performed before any files are pushed. |
| **FR-7** | If GitHub App authentication fails (JWT mint, IAT exchange, or private-key load), the response is 502 problem+json with code `GITHUB_AUTH_FAILED`. The underlying GitHub error is logged but **never** echoed to the client. |
| **FR-8** | The scaffold pipeline downloads the monorepo zip, extracts only the skeleton subfolder, writes the `AgentInput` payload (scaffolder keys stripped) to `config/agents-config.json`, and pushes every file into the target subfolder via the GitHub Contents API. YAML generation was removed — the JSON config is the single source of truth consumed by downstream tooling. |
| **FR-9** | All non-2xx responses use `application/problem+json` (RFC 7807) and carry `type`, `title`, `status`, `code`, `detail`, `instance`, `request_id` fields. |
| **FR-10** | Every response — success or error — carries an `X-Request-Id` response header. If the request supplied `X-Request-Id`, it is echoed; otherwise a fresh UUID4 is generated by `RequestIDMiddleware`. |
| **FR-11** | If the request body is empty or missing on `POST /scaffold`, the service falls back to reading `AGENT_INPUT_PATH` from disk. This **transitional** behaviour is kept for compatibility with the pre-refactor pipeline and will be removed in v0.2. |
| **FR-12** | Logs are JSON, one event per line, and every log line carries `request_id`. Logs **must never** include the GitHub App private key, the minted JWT, the IAT, or the bearer API key. |
| **FR-13** | The IAT is cached in memory and refreshed automatically 5 minutes before its 60-minute GitHub-issued expiry. JWT lifetime is 9 minutes (below the 10-minute hard limit) with a 60-second clock-skew buffer. |

## 5. Non-functional requirements

| ID | Requirement |
| --- | --- |
| **NFR-1** | p95 latency: `< 200 ms` for `/healthz` and `/templates`; `< 30 s` for `/scaffold` (bound by GitHub Contents API, file-by-file push). |
| **NFR-2** | All errors follow the problem+json contract (FR-9). |
| **NFR-3** | Structured JSON logs; every line carries `request_id` (FR-10). Log format conforms to the org logging schema (see CLAUDE.md §11). |
| **NFR-4** | No secrets in source. Settings via env vars / GCP Secret Manager (`app/settings.py`). |
| **NFR-5** | Test coverage `≥ 85%` statement coverage; CI blocks merges below the gate. |
| **NFR-6** | `ruff check`, `ruff format --check`, and `mypy --strict app/` pass with zero findings. |
| **NFR-7** | Layering: no module under `app/services/` or `app/core/` may import `fastapi`. Enforced by a test in `tests/test_layering.py`. |
| **NFR-8** | CORS: allowlist-driven via `Settings.cors_allowlist`. Default is **deny** (empty list). No wildcards in production config. |
| **NFR-9** | Idempotency by check-then-create: `POST /scaffold` performs an existence check before pushing. (True atomic idempotency is a v0.2 follow-up — see `plan.md` risks.) |

## 6. Data model

### `AgentInput` (request body of `POST /scaffold`)
The JSON body of `POST /scaffold` is `AgentInput` directly — there is no wrapper object.

Mirrors the `inputs/*.json` schema today.

```
AgentInput:
  scaffold_type:  str           # required; one of the supported types
  repo_name:      str           # required; 1..100 chars; matches ^[a-z0-9][a-z0-9_-]{0,99}$
  description:    str           # default: "Scaffolded by AURA platform"; <= 500 chars
  root_agent:     RootAgent     # required
  agents:         list[SubAgent]   # may be empty (single-agent case)
  custom_agents:  list[SubAgent]   # default: []  (multi-agent only)
```

### `RootAgent`
```
RootAgent:
  name:                     str
  agent_type:               str          # e.g. "LLMAgent"
  model:                    str          # e.g. "gemini-2.0-flash-001"
  description:              str
  instruction:              str
  generate_content_config:  GenerateContentConfig
  output_key:               str | None
  input_schema:             dict | None
  output_schema:            dict | None
  include_contents:         str | None
  planner:                  dict | None
  multiagent:               bool         # default false
```

### `SubAgent`
```
SubAgent:
  name:                     str
  agent_type:               str          # "LLMAgent" | "LoopAgent" | ...
  description:              str
  instruction:              str | None
  model:                    str | None
  generate_content_config:  GenerateContentConfig | None
  output_key:               str | None
  include_contents:         str | None
  rag_enabled:              bool         # default false
  workflow:                 bool         # default false
  max_iterations:           int | None   # LoopAgent only
  input_schema:             dict | None
  output_schema:            dict | None
  planner:                  dict | None
  tools:                    dict | None
  sub_agents:               list[SubAgent]   # default: []  (recursive)
```

### `GenerateContentConfig`
```
GenerateContentConfig:
  temperature:        float        # 0.0..2.0
  top_p:              float        # 0.0..1.0
  top_k:              int | None
  max_output_tokens:  int          # >= 1
```

### `ScaffoldResponse` (success body, 201)
```
ScaffoldResponse:
  job_id:        str       # ULID/uuid4
  status:        str       # "success"
  scaffold_type: str
  repo_url:      str       # https URL to the created subfolder
  config_path:   str       # path-in-repo to the generated agents-config.json
  template_used: str       # registry tuple as string
  created_at:    str       # ISO-8601 UTC
  message:       str
```

`AgentInput` and `ScaffoldResponse` use `extra="forbid"` — unknown top-level fields return 422. Nested agent models (`RootAgent`, `SubAgent`, `GenerateContentConfig`) use `extra="allow"` so that extension fields (e.g. `workflow`, `rag_enabled`) are preserved faithfully in `agents-config.json` without needing to enumerate every possible field in the schema.

## 7. Error model — problem+json

Every non-2xx response is `application/problem+json` shaped as:

```json
{
  "type":       "https://errors.aura.example.com/template-not-found",
  "title":      "Template not found",
  "status":     400,
  "code":       "TEMPLATE_NOT_FOUND",
  "detail":     "Unknown scaffold_type 'foo'. Supported: agent_clientapp, multiagent_orchestrator, ...",
  "instance":   "/scaffold",
  "request_id": "01HX2J0KQ8C8VZJ8M2QJ7E1B0F"
}
```

Defined `code` values (v0.1):

| code | HTTP | Raised by |
| --- | :---: | --- |
| `VALIDATION_ERROR` | 422 | Pydantic body validation |
| `UNAUTHORIZED` | 401 | Missing / wrong bearer token |
| `TEMPLATE_NOT_FOUND` | 400 | Unknown `scaffold_type` |
| `AGENT_ALREADY_EXISTS` | 409 | Target subfolder already in `aura-generated-agents` |
| `INVALID_AGENT_INPUT` | 400 | Semantic errors not caught by Pydantic (e.g., circular `sub_agents`) |
| `GITHUB_AUTH_FAILED` | 502 | JWT mint, IAT exchange, or private-key load failure |
| `SCAFFOLD_FAILED` | 500 | Pipeline failure after auth (download, extract, push) |

## 8. Pagination

`GET /templates` returns the full registry (≤ ~20 entries expected in foreseeable future) — pagination is not required for v0.1. If the registry grows beyond ~100 entries, add `limit` / `offset` query params with defaults `limit=20`, `offset=0`, max `limit=100`.

## 9. Versioning

The service version is exposed via `GET /healthz` (`version` field) and matches `pyproject.toml`'s `[project].version`. v0.1 is reserved for the SDD retrofit defined in this spec. Breaking changes bump the major version.

## 10. Open questions / deferred to v0.2

1. **`rag_pipeline` production readiness.** The registry entry exists; the skeleton folder and end-to-end scaffold flow need to ship before this is advertised. Guardrails and other AI component templates follow the same pattern.
2. **Atomic push.** Replace file-by-file Contents API calls with a single Git Trees + Commit API call so a failed scaffold leaves no partial folder behind.
3. **Concurrency.** Two simultaneous `POST /scaffold` for the same `repo_name` can both pass the existence check. Add a short-lived distributed lock or a unique-name index.
4. **Real OAuth/OIDC.** Replace static bearer with per-caller identities.
5. **Retry/backoff.** Transient GitHub 5xx and rate-limit responses are currently fatal; add retry with jitter on 502/503/504/429.
6. **Removing the `AGENT_INPUT_PATH` fallback (FR-11).** Once all known callers send a request body.
