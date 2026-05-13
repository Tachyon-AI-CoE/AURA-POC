"""
Typed domain exceptions and FastAPI exception handlers.

Services raise these exceptions; the handlers registered in app.main convert
them to RFC 7807 application/problem+json responses.
"""

from __future__ import annotations

import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.logging import request_id_var
from app.schemas.errors import Problem

logger = logging.getLogger("aura.errors")


# ---------------------------------------------------------------------------
# Domain exceptions
# ---------------------------------------------------------------------------


class AuraError(Exception):
    """Base for all typed AURA domain errors."""

    code: str = "INTERNAL_ERROR"
    status_code: int = 500


class TemplateNotFoundError(AuraError):
    code = "TEMPLATE_NOT_FOUND"
    status_code = 400


class AgentAlreadyExistsError(AuraError):
    code = "AGENT_ALREADY_EXISTS"
    status_code = 409


class GitHubAuthError(AuraError):
    code = "GITHUB_AUTH_FAILED"
    status_code = 502


class ScaffoldFailedError(AuraError):
    code = "SCAFFOLD_FAILED"
    status_code = 500


class InvalidAgentInputError(AuraError):
    code = "INVALID_AGENT_INPUT"
    status_code = 400


class UnauthorizedError(AuraError):
    code = "UNAUTHORIZED"
    status_code = 401


# ---------------------------------------------------------------------------
# Exception handlers (registered in app.main)
# ---------------------------------------------------------------------------


def _problem_response(
    status: int,
    code: str,
    detail: str,
    request_id: str,
) -> JSONResponse:
    title = code.replace("_", " ").title()
    body = Problem(
        title=title,
        status=status,
        detail=detail,
        code=code,
        request_id=request_id,
    )
    return JSONResponse(
        content=body.model_dump(),
        status_code=status,
        media_type="application/problem+json",
    )


async def aura_error_handler(request: Request, exc: AuraError) -> JSONResponse:
    request_id = request_id_var.get() or ""
    logger.error(
        "Domain error: %s — %s",
        exc.code,
        exc,
        extra={"app.request_id": request_id, "app.error_code": exc.code},
    )
    return _problem_response(exc.status_code, exc.code, str(exc), request_id)


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    request_id = request_id_var.get() or ""
    detail = "; ".join(
        f"{' -> '.join(str(loc) for loc in e['loc'])}: {e['msg']}" for e in exc.errors()
    )
    return _problem_response(422, "VALIDATION_ERROR", detail, request_id)


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = request_id_var.get() or ""
    logger.exception(
        "Unhandled exception",
        extra={"app.request_id": request_id},
    )
    return _problem_response(500, "INTERNAL_ERROR", "An unexpected error occurred.", request_id)
