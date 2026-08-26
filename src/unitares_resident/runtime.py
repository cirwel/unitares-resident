"""Provider-neutral Resident runtime built on the public UNITARES SDK."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from unitares_sdk.agent import CycleResult, GovernanceAgent
from unitares_sdk.client import GovernanceClient

from unitares_resident.config import ResidentConfig


@dataclass(frozen=True, slots=True)
class ResidentTurn:
    """One meaningful unit of agent work, ready for a governance check-in."""

    summary: str
    complexity: float = 0.5
    confidence: float = 0.5

    def __post_init__(self) -> None:
        if not self.summary.strip():
            raise ValueError("ResidentTurn.summary must not be empty")
        for name, value in (
            ("complexity", self.complexity),
            ("confidence", self.confidence),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1")


class TurnBackend(Protocol):
    """Provider or harness adapter that supplies the next completed turn."""

    async def next_turn(self) -> ResidentTurn | None:
        """Return completed work, or None when this cycle is idle."""


class ResidentAgent(GovernanceAgent):
    """Public-SDK resident shell with an injected reasoning backend."""

    def __init__(self, config: ResidentConfig, backend: TurnBackend) -> None:
        super().__init__(
            name=config.name,
            mcp_url=config.mcp_url,
            persistent=True,
            refuse_fresh_onboard=True,
            cycle_timeout_seconds=config.cycle_timeout_seconds,
        )
        self.config = config
        self.backend = backend

    async def run_cycle(
        self,
        client: GovernanceClient,
    ) -> CycleResult | None:
        del client  # Backends receive only their explicit ports, never Core internals.
        turn = await self.backend.next_turn()
        if turn is None:
            return None
        return CycleResult(
            summary=turn.summary,
            complexity=turn.complexity,
            confidence=turn.confidence,
        )
