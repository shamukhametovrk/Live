"""Помощники для эффектов на местах."""

from dataclasses import replace
from typing import assert_never

from ..ids import PlayerID
from ..state import Double, Effect, FullForce, PlayAlong, Seat, Shield, TryThis


def find[E: Effect](seat: Seat, kind: type[E]) -> E | None:
    """Эффект вида `kind` на месте, если он есть."""
    for effect in seat.effects:
        if isinstance(effect, kind):
            return effect
    return None


def without(seat: Seat, effect: Effect) -> Seat:
    return replace(seat, effects=tuple(e for e in seat.effects if e != effect))


def in_force(effect: Effect, turn: int) -> bool:
    """Принуждение действует со следующего хода после появления.

    Наложенное на себя в свой ход не мешает этому же ходу.
    """
    return turn > effect.turn


def expired(
    effect: Effect, owner: PlayerID, ended_turn: int, ended_active: PlayerID
) -> bool:
    """Истёк ли эффект с концом хода `ended_turn` игрока `ended_active`."""
    match effect:
        case Double():
            return True
        case Shield(turn=t):
            return ended_turn >= t + 1
        case PlayAlong(turn=t) | TryThis(turn=t):
            return ended_active == owner and ended_turn > t
        case FullForce():
            return False
        case _:
            assert_never(effect)
