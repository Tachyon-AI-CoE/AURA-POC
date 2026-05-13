"""
GitHub App Authentication
--------------------------
Step 1 → Mint a short-lived JWT signed with the App private key (9 min lifetime).
Step 2 → Exchange that JWT for an Installation Access Token (IAT, valid 60 min).

Private key precedence (defined in ``app.settings.Settings``):
  1. ``GITHUB_PRIVATE_KEY``       — inline PEM content
  2. ``GITHUB_PRIVATE_KEY_FILE``  — path to a .pem file (easiest for local .env)
  3. GCP Secret Manager via REST  — used on Cloud Run automatically

Behavior preserved verbatim from the pre-SDD ``github_app.py``; configuration
is now read from :class:`app.settings.Settings` instead of ``os.environ``.
"""

from __future__ import annotations

import base64
import contextlib
import logging
import subprocess
import time
from datetime import datetime
from pathlib import Path

import jwt  # PyJWT[crypto]
import requests

from app.settings import get_settings

logger = logging.getLogger("aura.github_auth")

# IAT in-memory cache (refresh 5 min before expiry).
_cached_iat: str | None = None
_iat_expires_at: float = 0.0


def _otel_span(name: str) -> contextlib.AbstractContextManager[None]:
    """No-op OpenTelemetry span hook.

    To wire a real tracer, replace the body with:
        return opentelemetry.trace.get_tracer(__name__).start_as_current_span(name)
    """
    return contextlib.nullcontext()


def _get_gcp_access_token() -> str:
    """Get a GCP access token from the Cloud Run metadata server.

    Works on any GCP compute. For local dev, falls back to ``gcloud auth
    application-default print-access-token``.
    """
    metadata_url = (
        "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token"
    )
    try:
        resp = requests.get(
            metadata_url,
            headers={"Metadata-Flavor": "Google"},
            timeout=5,
        )
        resp.raise_for_status()
        return str(resp.json()["access_token"])
    except Exception:
        logger.info("Metadata server not available, trying gcloud ADC token...")
        result = subprocess.run(
            ["gcloud", "auth", "application-default", "print-access-token"],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            raise RuntimeError(
                "Cannot get GCP access token. On Cloud Run this is automatic. "
                "Locally, run: gcloud auth application-default login"
            ) from None
        return result.stdout.strip()


def _load_private_key() -> str:
    """Load the GitHub App PEM private key. Never log the result."""
    settings = get_settings()

    if settings.github_private_key:
        inline = settings.github_private_key.get_secret_value().strip()
        if inline:
            logger.info("Private key loaded from GITHUB_PRIVATE_KEY env var")
            return inline

    if settings.github_private_key_file:
        path = settings.github_private_key_file.strip()
        if path:
            if not Path(path).is_file():
                raise FileNotFoundError(f"GITHUB_PRIVATE_KEY_FILE points to a missing file: {path}")
            with Path(path).open(encoding="utf-8") as f:
                pem = f.read().strip()
            logger.info("Private key loaded from file: %s", path)
            return pem

    # Cloud Run / GCP: load from Secret Manager via REST API.
    access_token = _get_gcp_access_token()
    url = (
        f"https://secretmanager.googleapis.com/v1/"
        f"projects/{settings.gcp_project_id}/secrets/"
        f"{settings.github_private_key_secret}/versions/latest:access"
    )
    resp = requests.get(
        url,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    if resp.status_code == 403:
        raise PermissionError(
            f"Service account does not have access to secret "
            f"'{settings.github_private_key_secret}'. "
            "Grant roles/secretmanager.secretAccessor to the Cloud Run service account."
        )
    resp.raise_for_status()
    encoded = resp.json()["payload"]["data"]
    pem = base64.b64decode(encoded).decode("utf-8")
    logger.info("Private key loaded from Secret Manager via REST")
    return pem


def _mint_app_jwt(private_key_pem: str) -> str:
    """Create a 9-minute JWT (below GitHub's 10-min hard limit) with 60s clock-skew buffer."""
    settings = get_settings()
    now = int(time.time())
    payload = {
        "iat": now - 60,
        "exp": now + (9 * 60),
        "iss": settings.github_app_id,
    }
    return jwt.encode(payload, private_key_pem, algorithm="RS256")


def get_installation_token() -> str:
    """Return a valid GitHub Installation Access Token.

    Caches in memory; auto-refreshes 5 min before the GitHub-issued expiry.
    Same external contract as the pre-SDD :func:`github_app.get_installation_token`.
    """
    with _otel_span("aura.get_installation_token"):
        return _fetch_installation_token()


def _fetch_installation_token() -> str:
    global _cached_iat, _iat_expires_at
    settings = get_settings()

    if _cached_iat and time.time() < (_iat_expires_at - 300):
        logger.debug("Using cached IAT token")
        return _cached_iat

    logger.info("Minting new GitHub Installation Access Token...")
    private_key = _load_private_key()
    app_jwt = _mint_app_jwt(private_key)

    url = (
        f"https://api.github.com/app/installations/{settings.github_installation_id}/access_tokens"
    )
    headers = {
        "Authorization": f"Bearer {app_jwt}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    resp = requests.post(url, headers=headers, timeout=15)
    if resp.status_code != 201:
        raise RuntimeError(f"GitHub IAT request failed: {resp.status_code} — {resp.text}")

    data = resp.json()
    _cached_iat = data["token"]

    expires_str = data.get("expires_at", "")
    try:
        dt = datetime.fromisoformat(expires_str.replace("Z", "+00:00"))
        _iat_expires_at = dt.timestamp()
    except Exception:
        _iat_expires_at = time.time() + 3600  # fallback: 1 hour

    logger.info("IAT token obtained. Expires: %s", expires_str)
    return _cached_iat
