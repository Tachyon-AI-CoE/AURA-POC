"""
Settings — single source of truth for all environment-driven configuration.

Replaces the scattered ``os.environ.get(...)`` calls that were in
``github_app.py`` and ``git_engine.py``. Read these once via :func:`get_settings`
and inject the result wherever it's needed.
"""

from __future__ import annotations

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- GitHub App auth ----
    github_app_id: str = Field(default="3599330")
    github_installation_id: str = Field(default="129468928")
    github_org: str = Field(default="Tachyon-AI-CoE")
    generated_agents_repo: str = Field(default="aura-generated-agents")

    # One of these three is required at runtime. Precedence:
    #   GITHUB_PRIVATE_KEY (inline PEM)
    #   GITHUB_PRIVATE_KEY_FILE (path)
    #   GCP Secret Manager (gcp_project_id + github_private_key_secret)
    github_private_key: SecretStr | None = None
    github_private_key_file: str | None = None
    github_private_key_secret: str = Field(default="github-app-private-key")
    gcp_project_id: str = Field(default="multi-agent-userstory")

    # ---- API auth (wired in M5) ----
    scaffold_api_key: SecretStr | None = None

    # ---- CORS (wired in M9) ----
    cors_allowlist: list[str] = Field(default_factory=list)

    # ---- Transitional fallback (FR-11) ----
    agent_input_path: str = Field(default="inputs/agent_input.json")

    # ---- Logging ----
    log_level: str = Field(default="INFO")

    @field_validator("cors_allowlist", mode="before")
    @classmethod
    def _split_cors(cls, v: object) -> object:
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v or []


_settings: Settings | None = None


def get_settings() -> Settings:
    """Return a cached Settings instance. Safe to call from any layer."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
