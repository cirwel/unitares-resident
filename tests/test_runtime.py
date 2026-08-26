from __future__ import annotations

import pytest

from unitares_resident import ResidentAgent, ResidentConfig, ResidentTurn


class StubBackend:
    def __init__(self, turn: ResidentTurn | None) -> None:
        self.turn = turn

    async def next_turn(self) -> ResidentTurn | None:
        return self.turn


@pytest.mark.asyncio
async def test_resident_turn_becomes_public_sdk_cycle_result():
    agent = ResidentAgent(
        ResidentConfig(),
        StubBackend(
            ResidentTurn(
                summary="answered a bounded request",
                complexity=0.4,
                confidence=0.8,
            )
        ),
    )
    result = await agent.run_cycle(None)  # type: ignore[arg-type]
    assert result is not None
    assert result.summary == "answered a bounded request"
    assert result.complexity == 0.4
    assert result.confidence == 0.8


@pytest.mark.asyncio
async def test_idle_backend_skips_checkin():
    agent = ResidentAgent(ResidentConfig(), StubBackend(None))
    assert await agent.run_cycle(None) is None  # type: ignore[arg-type]


@pytest.mark.parametrize("field", ["complexity", "confidence"])
def test_turn_state_is_bounded(field: str):
    values = {"summary": "work", field: 1.1}
    with pytest.raises(ValueError):
        ResidentTurn(**values)
