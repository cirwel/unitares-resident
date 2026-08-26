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
