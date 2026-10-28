"""Начало раунда (см. правила домена, «Начало раунда»)."""

from collections import Counter
from random import Random

from ..events import Event, RoundStarted
from ..ids import PlayerID
from ..state import Round, RoundResult, Seat, Settings
from .prepare import deal


def start_round(
    settings: Settings,
    players: tuple[PlayerID, ...],
    results: tuple[RoundResult, ...],
    rng: Random,
) -> tuple[Round, list[Event]]:
    """Новый раунд для невыбывших `players`."""
    start_health = rng.randint(*settings.health)
    circle = tuple(rng.sample(players, len(players)))
    first = _fair_first(players, results, rng)
    spread, dealt = deal(settings, circle, rng)
    round_ = Round(
        start_health=start_health,
        circle=circle,
        first=first,
        active=first,
        turn=1,
        seats=frozendict({p: Seat(start_health) for p in circle}),
        spread=spread,
    )
    return round_, [RoundStarted(start_health, circle, first), *dealt]


def _fair_first(
    players: tuple[PlayerID, ...],
    results: tuple[RoundResult, ...],
    rng: Random,
) -> PlayerID:
    """Тот, кто реже всех начинал раунды; при равенстве — случайный."""
    started = Counter(r.first for r in results)
    fewest = min(started[p] for p in players)
    return rng.choice(sorted(p for p in players if started[p] == fewest))
