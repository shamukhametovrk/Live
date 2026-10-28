"""Общее для выстрела и предметов, которые трогают каморы."""

from ..ids import PlayerID
from ..state import Chamber, Effect, Seat, TryThis
from .effects import find, without


def use_chamber(
    seats: dict[PlayerID, Seat], chambers: list[Chamber], i: int
) -> list[tuple[PlayerID, Effect]]:
    """Делает камору использованной и снимает все «Попробуй вот эту» на неё.

    Меняет `seats` и `chambers` на месте; возвращает снятые эффекты.
    """
    chambers[i] = Chamber(chambers[i].loaded, used=True)
    removed: list[tuple[PlayerID, Effect]] = []
    for owner, seat in seats.items():
        named = find(seat, TryThis)
        if named and named.chamber == i:
            seats[owner] = without(seat, named)
            removed.append((owner, named))
    return removed
