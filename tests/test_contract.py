from __future__ import annotations

import pytest

from unitares_resident.cli import run_live_doctor
from unitares_resident.config import ResidentConfig
from unitares_resident.contract import (
    REQUIRED_LIFECYCLE_CAPABILITIES,
    ContractCompatibilityError,
    validate_core_contract,
    validate_discovery,
)


def _contract(version: str = "1.1.0") -> dict:
    return {
        "schema": "unitares.interface-contract.v1",
        "version": version,
        "federation": {
            "negotiation": {"tool": "list_tools"},
            "mcp": {
                "version_specifier": ">=1.26.0,<3.0.0",
                "tested_majors": [1, 2],
                "newest_in_range_ci": "blocking",
            },
            "lifecycle": {
                "schema": "unitares.lifecycle-envelope.v1",
                "capabilities": list(REQUIRED_LIFECYCLE_CAPABILITIES),
                "success_envelope": {
                    "required": ["success", "tool", "next_action"]
                },
            },
        },
    }


def _discovery(version: str = "1.1.0") -> dict:
    return {
        "interface_contract": _contract(version),
        "tools": [{"name": name} for name in REQUIRED_LIFECYCLE_CAPABILITIES],
    }


def test_accepts_compatible_live_discovery():
    report = validate_discovery(_discovery())
    assert report["compatible"] is True
    assert report["interface"]["version"] == "1.1.0"
    assert report["lifecycle_envelope"] == "unitares.lifecycle-envelope.v1"


@pytest.mark.parametrize("version", ["1.0.0", "2.0.0", "banana"])
def test_rejects_unsupported_interface_versions(version):
    with pytest.raises(ContractCompatibilityError):
        validate_discovery(_discovery(version))


def test_rejects_missing_live_capability():
    tools = set(REQUIRED_LIFECYCLE_CAPABILITIES) - {"record_result"}
    with pytest.raises(ContractCompatibilityError, match="record_result"):
        validate_core_contract(_contract(), tools)


class _FakeClient:
    def __init__(self, payload, **kwargs):
        self.payload = payload
        self.kwargs = kwargs
        self.call = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return None

    async def call_tool(self, name, arguments):
        self.call = (name, arguments)
        return self.payload


@pytest.mark.asyncio
async def test_live_doctor_uses_public_list_tools_handshake():
    clients = []

    def factory(**kwargs):
        client = _FakeClient(_discovery(), **kwargs)
        clients.append(client)
        return client

    report = await run_live_doctor(ResidentConfig(), client_factory=factory)

    assert report["status"] == "ok"
    assert report["checks"]["contract_compatibility"]["compatible"] is True
    assert clients[0].call == ("list_tools", {"lite": True})


@pytest.mark.asyncio
async def test_live_doctor_reports_connection_failure():
    class FailingClient(_FakeClient):
        async def __aenter__(self):
            raise OSError("Core unavailable")

    report = await run_live_doctor(
        ResidentConfig(),
        client_factory=lambda **kwargs: FailingClient({}, **kwargs),
    )

    assert report["status"] == "error"
    assert report["checks"]["core_connection"]["status"] == "error"
    assert report["checks"]["contract_compatibility"]["status"] == "skipped"
