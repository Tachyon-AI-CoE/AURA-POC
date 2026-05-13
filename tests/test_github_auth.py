"""Tests for GitHub App auth service (T7.3, FR-13).

Covers: JWT minting, private-key loading (env/file/GCP), IAT fetch,
cache hit/miss, 5-min pre-expiry refresh, and GitHub failure handling.
All HTTP calls are mocked — no real GitHub or GCP contact.
"""

from __future__ import annotations

import base64
import time
from collections.abc import Generator
from datetime import UTC
from typing import Any
from unittest.mock import MagicMock, patch

import jwt
import pytest

from app.services import github_auth
from app.services.github_auth import (
    _load_private_key,
    _mint_app_jwt,
    get_installation_token,
)

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_settings(
    private_pem: str | None = None,
    key_file: str | None = None,
) -> MagicMock:
    s = MagicMock()
    s.github_app_id = "test-app-id"
    s.github_installation_id = "test-install-id"
    s.github_private_key_file = key_file
    s.gcp_project_id = "test-project"
    s.github_private_key_secret = "test-secret"
    if private_pem:
        s.github_private_key = MagicMock()
        s.github_private_key.get_secret_value.return_value = private_pem
    else:
        s.github_private_key = None
    return s


def _iat_response(token: str = "ghs_fake_iat") -> MagicMock:
    """Build a mock response that looks like the GitHub /access_tokens endpoint."""
    from datetime import datetime, timedelta

    expires = (datetime.now(UTC) + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    resp = MagicMock()
    resp.status_code = 201
    resp.json.return_value = {"token": token, "expires_at": expires}
    return resp


@pytest.fixture(scope="module")
def rsa_private_pem() -> str:
    """Throwaway RSA-2048 key — generated once per module to keep tests fast."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()


@pytest.fixture(autouse=True)
def _reset_iat_cache() -> Generator[None, None, None]:
    """Clear the module-level IAT cache before and after every test."""
    github_auth._cached_iat = None
    github_auth._iat_expires_at = 0.0
    yield
    github_auth._cached_iat = None
    github_auth._iat_expires_at = 0.0


# ---------------------------------------------------------------------------
# _mint_app_jwt
# ---------------------------------------------------------------------------


def test_jwt_claims_iss_iat_exp(rsa_private_pem: str) -> None:
    settings = _make_settings(rsa_private_pem)
    with patch("app.services.github_auth.get_settings", return_value=settings):
        token = _mint_app_jwt(rsa_private_pem)

    claims: dict[str, Any] = jwt.decode(token, options={"verify_signature": False})
    now = int(time.time())

    assert claims["iss"] == "test-app-id"
    # iat is now - 60s (clock-skew buffer)
    assert now - 120 <= claims["iat"] <= now
    # exp is roughly now + 9 min
    assert now + (9 * 60) - 10 <= claims["exp"] <= now + (9 * 60) + 10


def test_jwt_uses_rs256_algorithm(rsa_private_pem: str) -> None:
    settings = _make_settings(rsa_private_pem)
    with patch("app.services.github_auth.get_settings", return_value=settings):
        token = _mint_app_jwt(rsa_private_pem)

    header = jwt.get_unverified_header(token)
    assert header["alg"] == "RS256"


# ---------------------------------------------------------------------------
# _load_private_key
# ---------------------------------------------------------------------------


def test_load_key_from_inline_env(rsa_private_pem: str) -> None:
    settings = _make_settings(private_pem=rsa_private_pem)
    with patch("app.services.github_auth.get_settings", return_value=settings):
        result = _load_private_key()
    assert result == rsa_private_pem.strip()


def test_load_key_from_file(rsa_private_pem: str, tmp_path: Any) -> None:
    pem_file = tmp_path / "test.pem"
    pem_file.write_text(rsa_private_pem)
    settings = _make_settings(key_file=str(pem_file))
    with patch("app.services.github_auth.get_settings", return_value=settings):
        result = _load_private_key()
    assert result == rsa_private_pem.strip()


def test_load_key_file_not_found_raises() -> None:
    settings = _make_settings(key_file="/nonexistent/path/key.pem")
    with (
        patch("app.services.github_auth.get_settings", return_value=settings),
        pytest.raises(FileNotFoundError, match="GITHUB_PRIVATE_KEY_FILE"),
    ):
        _load_private_key()


def test_load_key_from_gcp_secret_manager(rsa_private_pem: str) -> None:
    settings = _make_settings()  # no inline key, no file
    b64_pem = base64.b64encode(rsa_private_pem.encode()).decode()
    secret_resp = MagicMock()
    secret_resp.status_code = 200
    secret_resp.raise_for_status = MagicMock()
    secret_resp.json.return_value = {"payload": {"data": b64_pem}}

    with (
        patch("app.services.github_auth.get_settings", return_value=settings),
        patch("app.services.github_auth._get_gcp_access_token", return_value="gcp-tok"),
        patch("app.services.github_auth.requests.get", return_value=secret_resp),
    ):
        result = _load_private_key()

    # GCP path does not call .strip() — result includes the trailing newline from PEM
    assert result == rsa_private_pem


def test_load_key_gcp_forbidden_raises(rsa_private_pem: str) -> None:
    settings = _make_settings()
    perm_resp = MagicMock()
    perm_resp.status_code = 403

    with (
        patch("app.services.github_auth.get_settings", return_value=settings),
        patch("app.services.github_auth._get_gcp_access_token", return_value="gcp-tok"),
        patch("app.services.github_auth.requests.get", return_value=perm_resp),
        pytest.raises(PermissionError),
    ):
        _load_private_key()


# ---------------------------------------------------------------------------
# _get_gcp_access_token
# ---------------------------------------------------------------------------


def test_gcp_token_from_metadata_server() -> None:
    from app.services.github_auth import _get_gcp_access_token

    meta_resp = MagicMock()
    meta_resp.status_code = 200
    meta_resp.raise_for_status = MagicMock()
    meta_resp.json.return_value = {"access_token": "meta-token"}

    with patch("app.services.github_auth.requests.get", return_value=meta_resp):
        token = _get_gcp_access_token()

    assert token == "meta-token"


def test_gcp_token_falls_back_to_gcloud(tmp_path: Any) -> None:
    from subprocess import CompletedProcess

    from app.services.github_auth import _get_gcp_access_token

    failing_resp = MagicMock()
    failing_resp.raise_for_status.side_effect = Exception("no metadata server")

    gcloud_result = CompletedProcess(args=[], returncode=0, stdout="gcloud-token\n")

    with (
        patch("app.services.github_auth.requests.get", side_effect=Exception("no metadata")),
        patch("app.services.github_auth.subprocess.run", return_value=gcloud_result),
    ):
        token = _get_gcp_access_token()

    assert token == "gcloud-token"


def test_gcp_token_both_fail_raises() -> None:
    from subprocess import CompletedProcess

    from app.services.github_auth import _get_gcp_access_token

    bad_result = CompletedProcess(args=[], returncode=1, stdout="", stderr="err")

    with (
        patch("app.services.github_auth.requests.get", side_effect=Exception("no metadata")),
        patch("app.services.github_auth.subprocess.run", return_value=bad_result),
        pytest.raises(RuntimeError, match="Cannot get GCP access token"),
    ):
        _get_gcp_access_token()


# ---------------------------------------------------------------------------
# get_installation_token
# ---------------------------------------------------------------------------


def test_fetches_fresh_token(rsa_private_pem: str) -> None:
    settings = _make_settings(private_pem=rsa_private_pem)
    with (
        patch("app.services.github_auth.get_settings", return_value=settings),
        patch("app.services.github_auth.requests.post", return_value=_iat_response()),
    ):
        token = get_installation_token()

    assert token == "ghs_fake_iat"
    assert github_auth._cached_iat == "ghs_fake_iat"


def test_cache_hit_skips_http(rsa_private_pem: str) -> None:
    settings = _make_settings(private_pem=rsa_private_pem)
    post_mock = MagicMock(return_value=_iat_response())

    with (
        patch("app.services.github_auth.get_settings", return_value=settings),
        patch("app.services.github_auth.requests.post", post_mock),
    ):
        t1 = get_installation_token()
        t2 = get_installation_token()

    assert t1 == t2 == "ghs_fake_iat"
    assert post_mock.call_count == 1  # second call used the in-memory cache


def test_expired_cache_triggers_refresh(rsa_private_pem: str) -> None:
    github_auth._cached_iat = "ghs_old"
    github_auth._iat_expires_at = time.time() - 10  # expired 10 s ago

    settings = _make_settings(private_pem=rsa_private_pem)
    post_mock = MagicMock(return_value=_iat_response())

    with (
        patch("app.services.github_auth.get_settings", return_value=settings),
        patch("app.services.github_auth.requests.post", post_mock),
    ):
        token = get_installation_token()

    assert token == "ghs_fake_iat"
    post_mock.assert_called_once()


def test_cache_within_5_min_window_triggers_refresh(rsa_private_pem: str) -> None:
    # Expires in 2 min — inside the 5-min refresh window
    github_auth._cached_iat = "ghs_near"
    github_auth._iat_expires_at = time.time() + 120

    settings = _make_settings(private_pem=rsa_private_pem)
    post_mock = MagicMock(return_value=_iat_response())

    with (
        patch("app.services.github_auth.get_settings", return_value=settings),
        patch("app.services.github_auth.requests.post", post_mock),
    ):
        token = get_installation_token()

    assert token == "ghs_fake_iat"
    post_mock.assert_called_once()


def test_cache_outside_5_min_window_not_refreshed(rsa_private_pem: str) -> None:
    # Expires in 10 min — outside the 5-min refresh window → cache is used
    github_auth._cached_iat = "ghs_still_valid"
    github_auth._iat_expires_at = time.time() + 600

    settings = _make_settings(private_pem=rsa_private_pem)
    post_mock = MagicMock()

    with (
        patch("app.services.github_auth.get_settings", return_value=settings),
        patch("app.services.github_auth.requests.post", post_mock),
    ):
        token = get_installation_token()

    assert token == "ghs_still_valid"
    post_mock.assert_not_called()


def test_github_non_201_raises_runtime_error(rsa_private_pem: str) -> None:
    settings = _make_settings(private_pem=rsa_private_pem)
    fail_resp = MagicMock()
    fail_resp.status_code = 401
    fail_resp.text = "Unauthorized"

    with (
        patch("app.services.github_auth.get_settings", return_value=settings),
        patch("app.services.github_auth.requests.post", return_value=fail_resp),
        pytest.raises(RuntimeError, match="GitHub IAT request failed"),
    ):
        get_installation_token()


def test_iat_expiry_parse_fallback(rsa_private_pem: str) -> None:
    """Malformed expires_at falls back to time.time() + 3600."""
    settings = _make_settings(private_pem=rsa_private_pem)
    bad_resp = MagicMock()
    bad_resp.status_code = 201
    bad_resp.json.return_value = {"token": "ghs_fallback", "expires_at": "not-a-date"}

    with (
        patch("app.services.github_auth.get_settings", return_value=settings),
        patch("app.services.github_auth.requests.post", return_value=bad_resp),
    ):
        token = get_installation_token()

    assert token == "ghs_fallback"
    # expiry should be roughly time.time() + 3600
    assert github_auth._iat_expires_at > time.time() + 3500
