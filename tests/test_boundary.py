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


# Names whose own literals DEFINE the boundary; scanning them would flag the
# check against itself.
BOUNDARY_DEFINITION_NAMES = {"PRIVILEGED_PATH_PREFIXES", "MCP_PATH_PREFIX"}

PRIVILEGED_ROUTE_MARKERS = (
    "/v1/tools/",
    "/v1/lease/",
    "/v1/agents",
    "/v1/kg",
    "/admin/",
)


def _boundary_definition_literals(tree: ast.AST) -> set[str]:
    """String constants belonging to the deny-list definitions themselves."""
    literals: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        names = {t.id for t in node.targets if isinstance(t, ast.Name)}
        if not names & BOUNDARY_DEFINITION_NAMES:
            continue
        for sub in ast.walk(node.value):
            if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                literals.add(sub.value)
    return literals


def test_package_hardcodes_no_privileged_core_route():
    """The import check cannot see a URL. This one can.

    Forbidding privileged imports proves Resident does not reach Core through a
    library. It says nothing about reaching Core over HTTP, which is how a
    privileged path would realistically appear — an import-clean request to a
    route that answers to a different authorization model.

    Deliberately NOT covered, so that a later reader does not over-read this:
      * provider traffic (OpenAI, Anthropic, local models) is expected and free;
      * a URL assembled at runtime from parts is invisible to a static scan.
    The configured Core endpoint is guarded separately, and at runtime, by
    config._reject_privileged_url.
    """
    violations: list[str] = []
    for path in Path("src/unitares_resident").rglob("*.py"):
        tree = ast.parse(path.read_text(), filename=str(path))
        allowed = _boundary_definition_literals(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            if node.value in allowed:
                continue
            lowered = node.value.lower()
            for marker in PRIVILEGED_ROUTE_MARKERS:
                if marker in lowered:
                    violations.append(
                        f"{path}:{node.lineno}: privileged Core route in a literal: "
                        f"{node.value!r}"
                    )
    assert not violations, "\n".join(violations)
