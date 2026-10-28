"""Разбор последствий (см. правила домена, «Последствия»).

Запускается после каждого действия, которое может что-то изменить в
ходе игры: выстрела, предмета, выбывания. Само действие делает только
своё, а здесь по порядку: гибель → конец раунда → конец хода → конец
ряда.
"""

from collections import Counter
from dataclasses import replace
from random import Random

from ..events import (
    Died,
    EffectRemoved,
    Event,
    GameFinished,
    RoundEnded,
    SpreadEnded,
    TurnPassed,
)
from ..ids import PlayerID
from ..state import (
    Finished,
    Game,
    InProgress,
    PlayAlong,
    Presence,
    Round,
    RoundResult,
    Shooting,
)
from .effects import expired, find, without
from .prepare import deal
from .round import start_round


def settle(
    game: InProgress,
    round_: Round,
    alive_before: tuple[PlayerID, ...],
    ends_turn: bool,
    rng: Random,
) -> tuple[Game, list[Event]]:
    """Последствия действия, после которого раунд стал `round_`.

    `alive_before` — живые до действия, `ends_turn` — закончило ли
    действие ход.
    """
    round_, events = _deaths(round_, alive_before)
    if len(round_.alive) <= 1:
        new_game, ended = _end_round(game, round_, rng)
        return new_game, events + ended
    if ends_turn or not round_.seats[round_.active].alive:
        round_, passed = _end_turn(round_)
        events += passed
    round_, spread_events = _end_spread(game, round_, rng)
    events += spread_events
    return replace(game, round=round_), events


def _deaths(
    round_: Round, alive_before: tuple[PlayerID, ...]
) -> tuple[Round, list[Event]]:
    dead = [p for p in alive_before if not round_.seats[p].alive]
    events: list[Event] = [Died(p) for p in dead]
    seats = dict(round_.seats)
    for owner, seat in round_.seats.items():
        named = find(seat, PlayAlong)
        if named and named.target in dead:
            seats[owner] = without(seat, named)
            events.append(EffectRemoved(owner, named))
    return replace(round_, seats=frozendict(seats)), events


def _end_round(
    game: InProgress, round_: Round, rng: Random
) -> tuple[Game, list[Event]]:
    (winner,) = round_.alive
    results = (*game.results, RoundResult(round_.first, winner))
    events: list[Event] = [RoundEnded(winner)]
    remaining = tuple(
        p for p in game.players if game.presence[p] is not Presence.WITHDRAWN
    )
    if len(results) >= game.settings.rounds or len(remaining) < 2:
        wins = Counter(r.winner for r in results)
        best = max((wins[p] for p in remaining), default=0)
        winners = tuple(p for p in remaining if wins[p] == best)
        events.append(GameFinished(winners))
        return Finished(game.players, game.presence, results), events
    new_round, started = start_round(game.settings, remaining, results, rng)
    game = replace(game, results=results, round=new_round)
    return game, events + started


def _end_turn(round_: Round) -> tuple[Round, list[Event]]:
    events: list[Event] = []
    seats = dict(round_.seats)
    for owner, seat in round_.seats.items():
        for effect in seat.effects:
            if expired(effect, owner, round_.turn, round_.active):
                seats[owner] = without(seats[owner], effect)
                events.append(EffectRemoved(owner, effect))
    circle = round_.circle
    start = circle.index(round_.active)
    active = next(
        p
        for i in range(1, len(circle) + 1)
        if seats[p := circle[(start + i) % len(circle)]].alive
    )
    turn = round_.turn + 1
    events.append(TurnPassed(active, turn))
    new_round = replace(
        round_, seats=frozendict(seats), active=active, turn=turn
    )
    return new_round, events


def _end_spread(
    game: InProgress, round_: Round, rng: Random
) -> tuple[Round, list[Event]]:
    spread = round_.spread
    if not isinstance(spread, Shooting) or not all(
        c.used for c in spread.chambers
    ):
        return round_, []
    preparing, dealt = deal(game.settings, round_.alive, rng)
    return replace(round_, spread=preparing), [SpreadEnded(), *dealt]
