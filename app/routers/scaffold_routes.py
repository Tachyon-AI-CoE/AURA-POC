"""POST /scaffold — create a new AI component (FR-3..FR-11)."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends
from pydantic import ValidationError

from app.core.template_registry import get_template_repo
from app.bearer_auth import bearer_auth
from app.exceptions import (
    AgentAlreadyExistsError,
    GitHubAuthError,
    InvalidAgentInputError,
    ScaffoldFailedError,
)
from app.schemas.agent_input import AgentInput
from app.schemas.scaffold_schema import ScaffoldResponse
from app.services.github_auth import get_installation_token
from app.services.scaffold_pipeline import scaffold_new_agent
from app.settings import Settings, get_settings

logger = logging.getLogger("aura.routers.scaffold")

router = APIRouter(tags=["Scaffold"])


@router.post("/scaffold", status_code=201, response_model=ScaffoldResponse)
async def create_scaffold(
    body: Annotated[AgentInput | None, Body()] = None,
    settings: Settings = Depends(get_settings),
    _: None = Depends(bearer_auth),
) -> Any:
     # Step 1: Generate a unique ID for this request
    job_id = str(uuid.uuid4())
    logger.info("[%s] Scaffold request received", job_id)

    if body is None:
         # Step 2: If no body provided, try reading from fallback file (backward compat)
        # FR-11: file-path fallback — deprecated, exists for backward compat.
        logger.warning(
            "[%s] No request body provided; falling back to AGENT_INPUT_PATH=%s (deprecated)",
            job_id,
            settings.agent_input_path,
        )
        try:
            # Open the file and read JSON
            with open(settings.agent_input_path, encoding="utf-8") as f:  # noqa: ASYNC230, PTH123
                raw: dict[str, Any] = json.load(f)
        except Exception as exc:
             # If file doesn't exist or isn't valid JSON, raise error
            raise InvalidAgentInputError(
                f"Cannot read fallback input file '{settings.agent_input_path}': {exc}"
            ) from exc
        try:
        # Validate the JSON against our schema
            body = AgentInput.model_validate(raw)
        except ValidationError as exc:
            raise InvalidAgentInputError(str(exc)) from exc


# Step 3: Log what we received
    logger.info(
        "[%s] scaffold_type=%s | repo_name=%s",
        job_id,
        body.scaffold_type,
        body.repo_name,
    )

    # Step 4: Look up the template for this scaffold_type
    # This returns (monorepo_name, subfolder) or raises TemplateNotFoundError
    template_repo = get_template_repo(body.scaffold_type)
    logger.info("[%s] Template: %s", job_id, template_repo)

    # Step 5: Get a GitHub authentication token
    try:
        iat_token = get_installation_token()  # Returns a valid GitHub token
    except Exception as exc:
        raise GitHubAuthError(str(exc)) from exc

    try:
        repo_url, config_path = scaffold_new_agent(
            template_repo_name=template_repo,
            agent_input=body,
            iat_token=iat_token,
        )
    except (AgentAlreadyExistsError, ScaffoldFailedError):
        raise
    except Exception as exc:
         # If it's any other error, wrap it as ScaffoldFailedError (will return 500)
        raise ScaffoldFailedError(str(exc)) from exc

    logger.info("[%s] Done -> %s", job_id, repo_url)

    return ScaffoldResponse(
        job_id=job_id,
        status="success",
        scaffold_type=body.scaffold_type,
        repo_url=repo_url,
        config_path=config_path,
        template_used=str(template_repo),
        created_at=datetime.now(UTC).isoformat(),
        message=f"Repository '{body.repo_name}' created successfully.",
    )


# flow:
# Client sends POST /scaffold with JSON body
#          ↓
# FastAPI validates JSON against AgentInput schema
#          ↓
# FastAPI calls Depends(bearer_auth) — checks Authorization header
#          ↓
# If auth fails → return 401 error
# If auth passes → continue to endpoint
#          ↓
# create_scaffold() runs:
#   1. Generate job_id
#   2. Read & validate body
#   3. Look up template
#   4. Get GitHub token (might fail → 502 error)
#   5. Run scaffold pipeline (might fail → 500 or 409 error)
#   6. Return 201 with ScaffoldResponse
