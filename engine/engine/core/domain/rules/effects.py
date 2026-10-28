"""Помощники для эффектов на местах."""

from dataclasses import replace

from ..state import Effect, Seat


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
