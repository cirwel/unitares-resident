"""Public UNITARES Core contract negotiation for Resident."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

INTERFACE_CONTRACT_SCHEMA = "unitares.interface-contract.v1"
MIN_INTERFACE_VERSION = (1, 1, 0)
MAX_INTERFACE_MAJOR = 1
LIFECYCLE_ENVELOPE_SCHEMA = "unitares.lifecycle-envelope.v1"
REQUIRED_LIFECYCLE_CAPABILITIES = (
    "start_session",
    "sync_state",
    "check_working_state",
    "record_result",
)
REQUIRED_SUCCESS_FIELDS = ("success", "tool", "next_action")


class ContractCompatibilityError(ValueError):
    """Core's public contract cannot safely support this Resident."""


def _version_triplet(value: object) -> tuple[int, int, int]:
    if not isinstance(value, str):
        raise ValueError("version is not a string")
    core = value.split("+", 1)[0].split("-", 1)[0]
    parts = core.split(".")
    if len(parts) != 3:
        raise ValueError("version must use major.minor.patch")
    return tuple(int(part) for part in parts)  # type: ignore[return-value]


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def validate_core_contract(
    contract: Mapping[str, Any],
    tool_names: Iterable[str],
) -> dict[str, Any]:
    """Validate a live or checked-in Core contract at the public boundary."""

    issues: list[str] = []
    schema = contract.get("schema")
    version = contract.get("version")
    if schema != INTERFACE_CONTRACT_SCHEMA:
        issues.append(
            f"expected schema {INTERFACE_CONTRACT_SCHEMA!r}, got {schema!r}"
        )

    try:
        parsed_version = _version_triplet(version)
    except (TypeError, ValueError) as exc:
        parsed_version = None
        issues.append(f"invalid interface version {version!r}: {exc}")
    if parsed_version is not None:
        if parsed_version[0] > MAX_INTERFACE_MAJOR:
            issues.append(
                f"interface version {version} is newer than supported major "
                f"{MAX_INTERFACE_MAJOR}"
            )
        elif parsed_version < MIN_INTERFACE_VERSION:
            minimum = ".".join(str(part) for part in MIN_INTERFACE_VERSION)
            issues.append(
                f"interface version {version} is older than required {minimum}"
            )

    federation = _mapping(contract.get("federation"))
    negotiation = _mapping(federation.get("negotiation"))
    if negotiation.get("tool") != "list_tools":
        issues.append("federation negotiation tool must be 'list_tools'")

    lifecycle = _mapping(federation.get("lifecycle"))
    lifecycle_schema = lifecycle.get("schema")
    if lifecycle_schema != LIFECYCLE_ENVELOPE_SCHEMA:
        issues.append(
            f"expected lifecycle schema {LIFECYCLE_ENVELOPE_SCHEMA!r}, "
            f"got {lifecycle_schema!r}"
        )

    declared_capabilities = set(lifecycle.get("capabilities") or [])
    observed_capabilities = set(tool_names)
    for capability in REQUIRED_LIFECYCLE_CAPABILITIES:
        if capability not in declared_capabilities:
            issues.append(f"lifecycle contract does not declare {capability!r}")
        if capability not in observed_capabilities:
            issues.append(f"list_tools did not advertise {capability!r}")

    success_envelope = _mapping(lifecycle.get("success_envelope"))
    required_fields = set(success_envelope.get("required") or [])
    missing_fields = set(REQUIRED_SUCCESS_FIELDS) - required_fields
    if missing_fields:
        issues.append(
            "lifecycle success envelope is missing required fields: "
            + ", ".join(sorted(missing_fields))
        )

    if issues:
        raise ContractCompatibilityError("; ".join(issues))

    mcp = _mapping(federation.get("mcp"))
    return {
        "compatible": True,
        "interface": {
            "schema": schema,
            "version": version,
        },
        "lifecycle_envelope": lifecycle_schema,
        "required_capabilities": list(REQUIRED_LIFECYCLE_CAPABILITIES),
        "mcp_support": {
            "server_specifier": mcp.get("version_specifier"),
            "tested_majors": mcp.get("tested_majors"),
            "newest_in_range_ci": mcp.get("newest_in_range_ci"),
        },
    }


def validate_discovery(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the result of the public ``list_tools(lite=true)`` call."""

    contract = payload.get("interface_contract")
    if not isinstance(contract, Mapping):
        raise ContractCompatibilityError(
            "list_tools response has no interface_contract object"
        )

    names: list[str] = []
    tools = payload.get("tools")
    if isinstance(tools, list):
        for entry in tools:
            if isinstance(entry, str):
                names.append(entry)
            elif isinstance(entry, Mapping) and isinstance(entry.get("name"), str):
                names.append(entry["name"])
    return validate_core_contract(contract, names)
