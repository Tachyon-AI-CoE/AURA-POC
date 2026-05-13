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
from app.deps import bearer_auth
from app.errors import (
    AgentAlreadyExistsError,
    GitHubAuthError,
    InvalidAgentInputError,
    ScaffoldFailedError,
)
from app.schemas.agent_input import AgentInput
from app.schemas.scaffold import ScaffoldResponse
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
    job_id = str(uuid.uuid4())
    logger.info("[%s] Scaffold request received", job_id)

    if body is None:
        # FR-11: file-path fallback — deprecated, exists for backward compat.
        logger.warning(
            "[%s] No request body provided; falling back to AGENT_INPUT_PATH=%s (deprecated)",
            job_id,
            settings.agent_input_path,
        )
        try:
            with open(settings.agent_input_path, encoding="utf-8") as f:  # noqa: ASYNC230, PTH123
                raw: dict[str, Any] = json.load(f)
        except Exception as exc:
            raise InvalidAgentInputError(
                f"Cannot read fallback input file '{settings.agent_input_path}': {exc}"
            ) from exc
        try:
            body = AgentInput.model_validate(raw)
        except ValidationError as exc:
            raise InvalidAgentInputError(str(exc)) from exc

    logger.info(
        "[%s] scaffold_type=%s | repo_name=%s",
        job_id,
        body.scaffold_type,
        body.repo_name,
    )

    template_repo = get_template_repo(body.scaffold_type)
    logger.info("[%s] Template: %s", job_id, template_repo)

    try:
        iat_token = get_installation_token()
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
