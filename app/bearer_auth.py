"""
FastAPI dependency functions.

bearer_auth — validates the Authorization: Bearer <token> header on
POST /scaffold (FR-4). If scaffold_api_key is not configured in Settings,
auth is bypassed with a warning (dev-only behaviour; set the key in prod).
"""
# Validates the bearer token on protected endpoints
from __future__ import annotations

import logging
import secrets

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.exceptions import UnauthorizedError
from app.settings import Settings, get_settings

logger = logging.getLogger("aura.bearer_auth")

_bearer_scheme = HTTPBearer(auto_error=False)


def bearer_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> None:
    api_key = settings.scaffold_api_key
    if api_key is None:
        logger.warning("SCAFFOLD_API_KEY not set — auth bypassed (not safe for production)")
        return
    # Check if client sent credentials AND they match the expected key
    if credentials is None or not secrets.compare_digest(
        credentials.credentials, # What client sent
        api_key.get_secret_value(), # What we expect
    ):
        raise UnauthorizedError("Invalid or missing bearer token")


# Flow: Client sends Authorization: Bearer mytoken123 → FastAPI extracts token
# → bearer_auth compares it to config → If match, endpoint runs. If not match, return 401 error

#this is used in /scaffold endpoint in create_scaffold func
