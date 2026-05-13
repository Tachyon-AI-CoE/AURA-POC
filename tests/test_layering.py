"""
Architecture guard: services/ and core/ must not import from fastapi.

An AST walk is used so the check works even if the modules cannot be imported
(e.g. missing optional dependencies in CI).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

APP_ROOT = Path(__file__).parent.parent / "app"
GUARDED_PACKAGES = ["services", "core"]


def _fastapi_imports(path: Path) -> list[str]:
    """Return list of lines that import from fastapi in the given .py file."""
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("fastapi"):
                    violations.append(f"{path}:{node.lineno}: import {alias.name}")
        elif isinstance(node, ast.ImportFrom) and (node.module or "").startswith("fastapi"):
            violations.append(f"{path}:{node.lineno}: from {node.module} import ...")
    return violations


def _collect_py_files(package: str) -> list[Path]:
    return list((APP_ROOT / package).rglob("*.py"))


@pytest.mark.parametrize("package", GUARDED_PACKAGES)
def test_no_fastapi_in_package(package: str) -> None:
    files = _collect_py_files(package)
    assert files, f"No Python files found under app/{package}/"
    all_violations: list[str] = []
    for py_file in files:
        all_violations.extend(_fastapi_imports(py_file))
    assert not all_violations, f"Forbidden fastapi imports found in app/{package}/:\n" + "\n".join(
        all_violations
    )
