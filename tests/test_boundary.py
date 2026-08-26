from __future__ import annotations

import ast
from pathlib import Path

FORBIDDEN_IMPORTS = {
    "src",
    "governance_core",
    "asyncpg",
    "psycopg",
    "psycopg2",
    "redis",
}


def test_package_uses_only_public_governance_boundary():
    violations: list[str] = []
    for path in Path("src/unitares_resident").rglob("*.py"):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules = [node.module]
            else:
                continue
            for module in modules:
                root = module.split(".", 1)[0]
                if root in FORBIDDEN_IMPORTS:
                    violations.append(f"{path}: forbidden import {module}")
    assert not violations, "\n".join(violations)
