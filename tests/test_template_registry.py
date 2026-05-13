"""Unit tests for app.core.template_registry."""

from __future__ import annotations

import pytest

from app.core.template_registry import (
    TEMPLATE_MONOREPO,
    TEMPLATE_REGISTRY,
    get_template_repo,
    list_supported_types,
)
from app.errors import TemplateNotFoundError


def test_known_type_returns_correct_tuple() -> None:
    monorepo, subfolder = get_template_repo("multiagent_orchestrator")
    assert monorepo == TEMPLATE_MONOREPO
    assert subfolder == TEMPLATE_REGISTRY["multiagent_orchestrator"]


def test_single_agent_type_resolves() -> None:
    _monorepo, subfolder = get_template_repo("single_agent")
    assert subfolder == "gcp-agent"


def test_unknown_type_raises_template_not_found() -> None:
    with pytest.raises(TemplateNotFoundError, match="unknown_type"):
        get_template_repo("unknown_type")


def test_list_supported_types_is_sorted() -> None:
    types = list_supported_types()
    assert types == sorted(types)


def test_list_supported_types_matches_registry() -> None:
    assert set(list_supported_types()) == set(TEMPLATE_REGISTRY.keys())
