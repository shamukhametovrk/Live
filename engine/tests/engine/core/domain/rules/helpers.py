"""Сборка состояний для тестов правил."""

from engine.core.domain.ids import PlayerID
from engine.core.domain.state import (
    Chamber,
    Effect,
    Preparing,
    Round,
    Seat,
    Shooting,
    Spread,
)

A, B, C = PlayerID(1), PlayerID(2), PlayerID(3)


def make_round(
    spread: Spread,
    *,
    seats: dict[PlayerID, Seat] | None = None,
    active: PlayerID = A,
    turn: int = 1,
) -> Round:
    seats = seats or {A: Seat(3), B: Seat(3), C: Seat(3)}
    return Round(
        start_health=3,
        circle=tuple(seats),
        first=A,
        active=active,
        turn=turn,
        seats=frozendict(seats),
        spread=spread,
    )


def shooting(*loaded: bool) -> Shooting:
    """Заряженный ряд без фишек: True — патрон."""
    return Shooting(
        chambers=tuple(Chamber(x) for x in loaded),
        chips=frozendict(),
        announced=sum(loaded),
    )


def preparing(size: int, offers: dict[PlayerID, tuple] | None = None):
    offers = offers or {A: (), B: (), C: ()}
    return Preparing(size, frozendict(offers))


def seat(health: int = 3, *effects: Effect, **kw) -> Seat:
    return Seat(health, effects=effects, **kw)
