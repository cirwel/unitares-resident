"""Environment-backed Resident configuration."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import urlparse

DEFAULT_NAME = "UNITARES Resident"
DEFAULT_MCP_URL = "http://127.0.0.1:8767/mcp/"
DEFAULT_INTERVAL_SECONDS = 60.0
DEFAULT_CYCLE_TIMEOUT_SECONDS = 120.0

# The non-privileged boundary is a claim about WHICH Core surface Resident can
# reach, and that is a property of the path, not of the host or port. Deployments
# move between loopback, a tailnet name, and a public gateway; the contract that
# must not move is "public MCP".
#
# Keyed on the path so the check stays portable: an operator can point Resident
# at any deployment, and cannot point it at a REST route that answers to a
# different authorization model.
MCP_PATH_PREFIX = "/mcp"

# Core's non-MCP surfaces. Reaching any of these would put Resident on a
# different authorization path than the one ARCHITECTURE.md describes, which is
# the whole content of "receives no privileged scoring or policy path".
PRIVILEGED_PATH_PREFIXES = (
    "/v1/tools/",     # direct tool dispatch, bypasses the MCP envelope
    "/v1/lease/",     # surface lease plane, bearer-scoped
    "/v1/agents",     # orchestrator control
    "/v1/kg",         # knowledge graph REST
    "/admin",
)


def _positive_float(env: Mapping[str, str], name: str, default: float) -> float:
    raw = env.get(name)
    if raw is None:
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number, got {raw!r}") from exc
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return value


def _reject_privileged_url(url: str) -> None:
    """Fail closed unless the URL names the public MCP surface.

    ``startswith("http")`` alone accepts every Core REST route, so the import
    boundary in ``tests/test_boundary.py`` could pass while an operator pointed
    the runtime straight at tool dispatch. Import-checking cannot see this:
    reaching a privileged route is a configuration act, not a code one.

    Provider traffic is deliberately NOT constrained here. This function scopes
    exactly one thing — the Core endpoint Resident is allowed to be aimed at.
    """
    path = urlparse(url).path or "/"
    normalized = path.rstrip("/").lower() or "/"

    for prefix in PRIVILEGED_PATH_PREFIXES:
        if normalized.startswith(prefix.rstrip("/")):
            raise ValueError(
                f"UNITARES_MCP_URL must not name a privileged Core route: {path!r} "
                f"matches {prefix!r}. Resident is an ordinary governed client and "
                f"reaches Core only through the public MCP endpoint."
            )

    is_mcp = normalized == MCP_PATH_PREFIX or normalized.startswith(
        MCP_PATH_PREFIX + "/"
    )
    if not is_mcp:
        raise ValueError(
            f"UNITARES_MCP_URL must address the public MCP endpoint "
            f"(path {MCP_PATH_PREFIX!r}), got {path!r}. Host and port are free so "
            f"any deployment works; the surface is not."
        )


@dataclass(frozen=True, slots=True)
class ResidentConfig:
    """Small, provider-neutral configuration for the runtime shell."""

    name: str = DEFAULT_NAME
    mcp_url: str = DEFAULT_MCP_URL
    interval_seconds: float = DEFAULT_INTERVAL_SECONDS
    cycle_timeout_seconds: float = DEFAULT_CYCLE_TIMEOUT_SECONDS

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> ResidentConfig:
        source = os.environ if env is None else env
        name = source.get("UNITARES_RESIDENT_NAME", DEFAULT_NAME).strip()
        mcp_url = source.get("UNITARES_MCP_URL", DEFAULT_MCP_URL).strip()
        if not name:
            raise ValueError("UNITARES_RESIDENT_NAME must not be empty")
        if not mcp_url.startswith(("http://", "https://")):
            raise ValueError("UNITARES_MCP_URL must be an http(s) URL")
        _reject_privileged_url(mcp_url)
        return cls(
            name=name,
            mcp_url=mcp_url,
            interval_seconds=_positive_float(
                source,
                "UNITARES_RESIDENT_INTERVAL_SECONDS",
                DEFAULT_INTERVAL_SECONDS,
            ),
            cycle_timeout_seconds=_positive_float(
                source,
                "UNITARES_RESIDENT_CYCLE_TIMEOUT_SECONDS",
                DEFAULT_CYCLE_TIMEOUT_SECONDS,
            ),
        )

    def public_summary(self) -> dict[str, Any]:
        """Return non-secret configuration suitable for doctor output."""

        return asdict(self)
