"""Environment-backed Resident configuration."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any

DEFAULT_NAME = "UNITARES Resident"
DEFAULT_MCP_URL = "http://127.0.0.1:8767/mcp/"
DEFAULT_INTERVAL_SECONDS = 60.0
DEFAULT_CYCLE_TIMEOUT_SECONDS = 120.0


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
