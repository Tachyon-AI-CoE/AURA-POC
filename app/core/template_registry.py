"""
Template Registry
-----------------
Maps ``scaffold_type`` → ``(monorepo, subfolder)`` inside the AURA-POC monorepo.

All scaffolder templates live inside one repo: ``Tachyon-AI-CoE/AURA-POC``.
Each template is a subfolder within that repo. To add a new component type:

1. Drop a skeleton folder into the AURA-POC monorepo.
2. Add a row below.
3. Add a test case in ``tests/test_template_registry.py``.
"""

# mapping file which go download template acc to selection
from __future__ import annotations

# Single source repo containing all scaffolder templates as subfolders.
TEMPLATE_MONOREPO = "AURA-POC"

# Registry: scaffold_type → subfolder name inside AURA-POC.
# Today scaffolds agents and multiagent. ``rag_pipeline`` is registered but is
# a planned future template (see spec.md §3, §10).
TEMPLATE_REGISTRY: dict[str, str] = {
    "multiagent_orchestrator": "gcp-multiagent-orchestrator-new-agents",
    "multiagent_workflow": "gcp-multiagent-workflow-new-agents",
    "single_agent": "gcp-agent",
    "single_agent_api": "gcp-agent-api/skeleton",
    "agent_clientapp": "gcp-agent-clientapp",
    "rag_pipeline": "gcp-rag-dataflow-pipeline",  
}


def get_template_repo(scaffold_type: str) -> tuple[str, str]:
    """Return ``(monorepo, subfolder)`` for the given scaffold type.

    Raises :class:`app.errors.TemplateNotFoundError` if the type is not registered.
    """
    from app.exceptions import TemplateNotFoundError  # local import avoids circular at module load

    subfolder = TEMPLATE_REGISTRY.get(scaffold_type)
    if not subfolder:
        supported = ", ".join(sorted(TEMPLATE_REGISTRY.keys()))
        raise TemplateNotFoundError(
            f"Unknown scaffold_type '{scaffold_type}'. Supported types: {supported}"
        )
    return TEMPLATE_MONOREPO, subfolder


def list_supported_types() -> list[str]:
    return sorted(TEMPLATE_REGISTRY.keys())
