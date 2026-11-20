"""Verify strict separation between pure-Python domain layers and UI frontends."""

from __future__ import annotations

import ast
from pathlib import Path

DOMAIN_DIRS = ("core", "data", "entities", "systems")
FORBIDDEN_IMPORTS = {"pygame", "pygame_ce", "pygame_gui"}


def test_domain_modules_never_import_pygame() -> None:
    src_root = Path(__file__).resolve().parents[1] / "src"
    violations: list[str] = []

    for sub in DOMAIN_DIRS:
        for py_file in (src_root / sub).rglob("*.py"):
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        top = alias.name.split(".")[0]
                        if top in FORBIDDEN_IMPORTS:
                            violations.append(f"{py_file.name}: import {alias.name}")
                elif isinstance(node, ast.ImportFrom) and node.module:
                    top = node.module.split(".")[0]
                    if top in FORBIDDEN_IMPORTS:
                        violations.append(f"{py_file.name}: from {node.module} import ...")

    assert violations == []
