from __future__ import annotations

import pytest

from unitares_resident.config import ResidentConfig


def test_defaults_are_local_and_provider_neutral():
    config = ResidentConfig.from_env({})
    assert config.name == "UNITARES Resident"
    assert config.mcp_url == "http://127.0.0.1:8767/mcp/"
    assert config.interval_seconds == 60.0
    assert config.cycle_timeout_seconds == 120.0


def test_environment_overrides_are_typed():
    config = ResidentConfig.from_env(
        {
            "UNITARES_RESIDENT_NAME": "Lumen",
            "UNITARES_MCP_URL": "https://governance.example/mcp/",
            "UNITARES_RESIDENT_INTERVAL_SECONDS": "15.5",
            "UNITARES_RESIDENT_CYCLE_TIMEOUT_SECONDS": "90",
        }
    )
    assert config.name == "Lumen"
    assert config.interval_seconds == 15.5
    assert config.cycle_timeout_seconds == 90.0


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("UNITARES_RESIDENT_INTERVAL_SECONDS", "0"),
        ("UNITARES_RESIDENT_CYCLE_TIMEOUT_SECONDS", "never"),
    ],
)
def test_invalid_durations_fail_closed(name: str, value: str):
    with pytest.raises(ValueError):
        ResidentConfig.from_env({name: value})


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:8767/mcp/",
        "http://127.0.0.1:8767/mcp",
        "https://governance.example/mcp/",
        "http://host.example:9999/mcp/",
    ],
)
def test_public_mcp_endpoints_are_accepted_on_any_host(url: str):
    """Host and port are deployment detail; the surface is the contract."""
    assert ResidentConfig.from_env({"UNITARES_MCP_URL": url}).mcp_url == url


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:8767/v1/tools/call",
        "http://127.0.0.1:8788/v1/lease/acquire",
        "http://127.0.0.1:8789/v1/agents",
        "http://127.0.0.1:8767/v1/kg/search",
        "http://127.0.0.1:8767/admin/reset",
    ],
)
def test_privileged_core_routes_fail_closed(url: str):
    """The non-privileged boundary is a runtime claim, not only an import one.

    tests/test_boundary.py proves Resident imports nothing privileged. It cannot
    prove Resident is not POINTED at something privileged — that is configuration,
    and before this check `startswith("http")` accepted every route below.
    """
    with pytest.raises(ValueError, match="privileged Core route"):
        ResidentConfig.from_env({"UNITARES_MCP_URL": url})


@pytest.mark.parametrize(
    "url",
    ["http://127.0.0.1:8767/", "http://127.0.0.1:8767", "https://example.net/api/v2"],
)
def test_non_mcp_paths_fail_closed(url: str):
    """Anything that is not the MCP surface is refused, not merely known-bad ones.

    An allowlist rather than a denylist: a Core route added tomorrow is rejected
    by default instead of silently permitted until someone remembers to list it.
    """
    with pytest.raises(ValueError, match="public MCP endpoint"):
        ResidentConfig.from_env({"UNITARES_MCP_URL": url})
