"""Снимок `MatchState`: неизменяемость и сравнение по значению."""

import dataclasses

import pytest

from engine.core.domain.enums import ChamberState
from engine.core.domain.ids import PlayerID
from engine.core.domain.value_objects import (
    ChamberRowState,
    MatchState,
    RoundState,
    SeatState,
)

A, B = PlayerID(1), PlayerID(2)


def make_state(**overrides: object) -> MatchState:
    seat = SeatState(health_points=3, items=(), effects=(), chips=0)
    stage = RoundState(
        row=ChamberRowState((ChamberState.EMPTY,), (1,)),
        initial_cartridges=0,
        layouts=frozendict(),  # type: ignore
        revealed=frozendict(),  # type: ignore
    )
    fields: dict[str, object] = {
        "turn_circle": (A, B),
        "active": A,
        "turn_number": 1,
        "seats": frozendict({A: seat, B: seat}),  # type: ignore
        "stage": stage,
    }
    fields.update(overrides)
    return MatchState(**fields)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "field", [f.name for f in dataclasses.fields(MatchState)]
)
def test_fields_cannot_be_reassigned(field: str) -> None:
    state = make_state()
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(state, field, None)


def test_equal_by_value_and_hashable() -> None:
    assert make_state() == make_state()
    assert len({make_state(), make_state()}) == 1
    assert make_state(active=B) != make_state()
