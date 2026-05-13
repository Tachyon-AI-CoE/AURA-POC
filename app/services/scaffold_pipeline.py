"""
Scaffold Pipeline
-----------------
End-to-end orchestration: downloads the skeleton from the AURA-POC monorepo,
writes the agents-config.json payload into config/, and pushes every file into
aura-generated-agents/<repo_name>/ via the GitHub Contents API.

Generated components are pushed as subfolders inside one shared repo:

    aura-generated-agents/
      <repo_name>/
        config/agents-config.json
        src/...

Uses the GitHub Contents API throughout — no git binary needed.
"""

from __future__ import annotations

import base64
import contextlib
import io
import json
import logging
import os
import shutil
import stat
import tempfile
import zipfile
from collections.abc import Callable
from pathlib import Path

import requests

from app.errors import AgentAlreadyExistsError, ScaffoldFailedError
from app.schemas.agent_input import AgentInput
from app.settings import get_settings

logger = logging.getLogger("aura.scaffold_pipeline")

GITHUB_API = "https://api.github.com"


def _otel_span(name: str) -> contextlib.AbstractContextManager[None]:
    """No-op OpenTelemetry span hook.

    To wire a real tracer, replace the body with:
        return opentelemetry.trace.get_tracer(__name__).start_as_current_span(name)
    """
    return contextlib.nullcontext()


# Top-level AgentInput keys that are scaffolder metadata, not agent config.
_SCAFFOLDER_KEYS = {"scaffold_type", "repo_name", "description"}


def _headers(iat_token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {iat_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def ensure_generated_agents_repo(iat_token: str) -> str:
    """Ensure the shared ``aura-generated-agents`` repo exists in the org.

    Creates it if it does not yet exist (first-time setup). Returns the repo's
    HTML URL.
    """
    settings = get_settings()
    org = settings.github_org
    repo = settings.generated_agents_repo

    url = f"{GITHUB_API}/repos/{org}/{repo}"
    resp = requests.get(url, headers=_headers(iat_token), timeout=15)

    if resp.status_code == 200:
        logger.info("Shared repo exists: %s/%s", org, repo)
        return str(resp.json()["html_url"])

    if resp.status_code == 404:
        logger.info("Creating shared repo: %s/%s", org, repo)
        create_url = f"{GITHUB_API}/orgs/{org}/repos"
        payload = {
            "name": repo,
            "description": "AURA Platform — all generated components live here as subfolders",
            "private": True,
            "auto_init": True,
            "has_issues": True,
            "has_projects": False,
            "has_wiki": False,
        }
        create_resp = requests.post(
            create_url, json=payload, headers=_headers(iat_token), timeout=20
        )
        create_resp.raise_for_status()
        html_url: str = create_resp.json()["html_url"]
        logger.info("Shared repo created: %s", html_url)
        return html_url

    resp.raise_for_status()
    raise ScaffoldFailedError(f"Unexpected response from GitHub: {resp.status_code}")


def _check_agent_folder_exists(agent_folder: str, iat_token: str) -> bool:
    """Return True if ``<agent_folder>/config`` already exists in the shared repo."""
    settings = get_settings()
    url = (
        f"{GITHUB_API}/repos/{settings.github_org}/{settings.generated_agents_repo}"
        f"/contents/{agent_folder}/config"
    )
    resp = requests.get(url, headers=_headers(iat_token), timeout=15)
    return bool(resp.status_code == 200)


def _download_subfolder_from_monorepo(
    monorepo_name: str,
    subfolder: str,
    iat_token: str,
    dest_dir: str,
) -> None:
    """Download the monorepo zip and extract only ``<subfolder>/skeleton/`` into ``dest_dir``."""
    settings = get_settings()
    url = f"{GITHUB_API}/repos/{settings.github_org}/{monorepo_name}/zipball/HEAD"
    logger.info("Downloading monorepo zip: %s/%s", settings.github_org, monorepo_name)

    resp = requests.get(
        url,
        headers=_headers(iat_token),
        timeout=120,
        allow_redirects=True,
        stream=True,
    )
    resp.raise_for_status()

    zip_bytes = io.BytesIO()
    for chunk in resp.iter_content(chunk_size=8192):
        zip_bytes.write(chunk)
    zip_bytes.seek(0)
    logger.info("Monorepo zip downloaded")

    extracted_count = 0
    with zipfile.ZipFile(zip_bytes) as zf:
        members = zf.namelist()
        zip_prefix = members[0].split("/")[0] + "/"
        skeleton_prefix = zip_prefix + subfolder.rstrip("/") + "/skeleton/"
        logger.info("Extracting skeleton contents from: %s", skeleton_prefix)

        for member in members:
            if not member.startswith(skeleton_prefix):
                continue
            relative_path = member[len(skeleton_prefix) :]
            if not relative_path:
                continue
            dest_path = Path(dest_dir) / relative_path
            if member.endswith("/"):
                dest_path.mkdir(parents=True, exist_ok=True)
            else:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(member) as src, dest_path.open("wb") as dst:
                    dst.write(src.read())
                extracted_count += 1

    if extracted_count == 0:
        zip_bytes.seek(0)
        available: set[str] = set()
        with zipfile.ZipFile(zip_bytes) as zf2:
            for m in zf2.namelist():
                parts = m[len(zip_prefix) :].split("/")
                if parts[0]:
                    available.add(parts[0])
        raise ScaffoldFailedError(
            f"Subfolder '{subfolder}' not found in {monorepo_name}, "
            f"or has no skeleton/ folder inside it. "
            f"Available top-level folders: {sorted(available)}"
        )

    logger.info("Extracted %d files from '%s'", extracted_count, subfolder)


def _push_files_into_subfolder(
    agent_folder: str,
    workdir: str,
    iat_token: str,
    branch: str = "main",
    commit_message: str = "chore: add component via AURA orchestrator",
) -> None:
    """Push all files from ``workdir`` into ``aura-generated-agents/<agent_folder>/``."""
    settings = get_settings()
    org = settings.github_org
    repo = settings.generated_agents_repo

    files_to_push: list[tuple[str, str]] = []
    for root, dirs, files in os.walk(workdir):
        dirs[:] = [d for d in dirs if d != ".git"]
        for fname in files:
            full_path = str(Path(root) / fname)
            rel_path = os.path.relpath(full_path, workdir).replace(os.sep, "/")
            github_path = f"{agent_folder}/{rel_path}"
            files_to_push.append((github_path, full_path))

    logger.info(
        "Pushing %d files into %s/%s/%s/",
        len(files_to_push),
        org,
        repo,
        agent_folder,
    )

    for i, (github_path, full_path) in enumerate(files_to_push):
        with Path(full_path).open("rb") as f:
            content_b64 = base64.b64encode(f.read()).decode("utf-8")

        url = f"{GITHUB_API}/repos/{org}/{repo}/contents/{github_path}"

        sha: str | None = None
        check_resp = requests.get(url, headers=_headers(iat_token), timeout=15)
        if check_resp.status_code == 200:
            sha = check_resp.json().get("sha")

        payload: dict[str, str] = {
            "message": commit_message,
            "content": content_b64,
            "branch": branch,
        }
        if sha:
            payload["sha"] = sha

        resp = requests.put(url, json=payload, headers=_headers(iat_token), timeout=30)

        if resp.status_code not in (200, 201):
            logger.error("Failed to push %s: %s %s", github_path, resp.status_code, resp.text)
            resp.raise_for_status()

        if (i + 1) % 10 == 0 or (i + 1) == len(files_to_push):
            logger.info("  Pushed %d/%d files...", i + 1, len(files_to_push))

    logger.info("All %d files pushed into /%s", len(files_to_push), agent_folder)


def _safe_rmtree(path: str) -> None:
    def _on_error(func: Callable[..., object], fpath: str, exc_info: object) -> None:
        Path(fpath).chmod(stat.S_IWRITE)
        func(fpath)

    shutil.rmtree(path, onerror=_on_error)


def scaffold_new_agent(
    template_repo_name: tuple[str, str],
    agent_input: AgentInput,
    iat_token: str,
) -> tuple[str, str]:
    """Full scaffold flow.

    Pushes the component into a subfolder of ``aura-generated-agents``:

        aura-generated-agents/
          <repo_name>/
            config/agents-config.json
            src/...
            cloudbuild.yaml

    Returns ``(subfolder_url, config_path)``.
    """
    with _otel_span("aura.scaffold_new_agent"):
        return _run_scaffold(template_repo_name, agent_input, iat_token)


def _run_scaffold(
    template_repo_name: tuple[str, str],
    agent_input: AgentInput,
    iat_token: str,
) -> tuple[str, str]:
    monorepo_name, subfolder = template_repo_name
    repo_name = agent_input.repo_name
    description = agent_input.description

    settings = get_settings()
    workdir = tempfile.mkdtemp(prefix=f"scaffold-{repo_name}-")

    try:
        ensure_generated_agents_repo(iat_token)

        if _check_agent_folder_exists(repo_name, iat_token):
            raise AgentAlreadyExistsError(
                f"Component '{repo_name}' already exists in "
                f"{settings.generated_agents_repo}. "
                "Use a different repo_name."
            )

        if subfolder:
            _download_subfolder_from_monorepo(monorepo_name, subfolder, iat_token, workdir)

        # Write agent config (scaffolder keys stripped) to config/agents-config.json.
        config_dir = Path(workdir) / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        agent_config = agent_input.model_dump(
            mode="json",
            exclude=_SCAFFOLDER_KEYS,
        )

        agents_config_path = config_dir / "agents-config.json"
        with agents_config_path.open("w", encoding="utf-8") as f:
            json.dump(agent_config, f, indent=2, ensure_ascii=False)

        logger.info("agents-config.json written into /config")

        _push_files_into_subfolder(
            agent_folder=repo_name,
            workdir=workdir,
            iat_token=iat_token,
            branch="main",
            commit_message=(
                f"feat: add {repo_name} via AURA orchestrator\n\n"
                f"Template: {monorepo_name}/{subfolder}\n"
                f"Description: {description}"
            ),
        )

        # NOTE: Cloud Build trigger creation is not yet implemented.
        # When wired, call the Cloud Build API here to trigger the ADK YAML
        # generation step that reads agents-config.json.
        logger.warning(
            "Cloud Build trigger not wired — agents-config.json pushed but "
            "no build triggered for %s",
            repo_name,
        )

        subfolder_url = (
            f"https://github.com/{settings.github_org}/"
            f"{settings.generated_agents_repo}/tree/main/{repo_name}"
        )
        return subfolder_url, f"{repo_name}/config/agents-config.json"

    except (AgentAlreadyExistsError, ScaffoldFailedError):
        raise
    except Exception as exc:
        logger.error("Scaffold failed: %s", exc)
        raise ScaffoldFailedError(str(exc)) from exc

    finally:
        _safe_rmtree(workdir)
        logger.info("Cleaned up temp workdir")
