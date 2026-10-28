from dataclasses import replace
from random import Random

from engine.core.domain.commands import Shoot
from engine.core.domain.events import (
    Died,
    EffectRemoved,
    GameFinished,
    RoundEnded,
    RoundStarted,
    SpreadEnded,
    TurnPassed,
)
from engine.core.domain.rules.settle import settle
from engine.core.domain.rules.shoot import shoot
from engine.core.domain.state import (
    Double,
    Finished,
    InProgress,
    PlayAlong,
    Preparing,
    Presence,
    Round,
    RoundResult,
    Settings,
    Shield,
)
from tests.engine.core.domain.rules.helpers import (
    A,
    B,
    C,
    make_round,
    seat,
    shooting,
)


def game_of(round_: Round, **kw) -> InProgress:
    players = (A, B, C)
    return InProgress(
        settings=kw.get("settings", Settings()),
        players=players,
        presence=frozendict(
            kw.get("presence", dict.fromkeys(players, Presence.PRESENT))
        ),
        results=kw.get("results", ()),
        round=round_,
    )


def fire(game: InProgress, actor, cmd):
    """Выстрел и разбор его последствий."""
    round_, events, ends = shoot(game.round, actor, cmd)
    new_game, more = settle(game, round_, game.round.alive, ends, Random(0))
    return new_game, events + more


def end_turn(game: InProgress) -> InProgress:
    """Ход кончается без действия: холостой в соседа."""
    r = replace(game.round, spread=shooting(False, False, False))
    target = next(p for p in r.alive if p != r.active)
    new_game, _ = fire(replace(game, round=r), r.active, Shoot(0, target))
    return new_game


def test_kill_passes_turn_over_the_dead_and_frees_named_target():
    seats = {A: seat(), B: seat(1), C: seat(3, PlayAlong(1, B))}
    game = game_of(make_round(shooting(True, False), seats=seats))
    game, events = fire(game, A, Shoot(0, B))
    assert Died(B) in events
    assert EffectRemoved(C, PlayAlong(1, B)) in events
    assert events[-1] == TurnPassed(C, 2)


def test_last_kill_ends_round_and_starts_next():
    seats = {A: seat(), B: seat(1), C: seat(0)}
    game = game_of(make_round(shooting(True, False), seats=seats))
    game, events = fire(game, A, Shoot(0, B))
    assert RoundEnded(A) in events
    assert any(isinstance(e, RoundStarted) for e in events)
    assert game.results == (RoundResult(A, A),)


def test_last_round_finishes_game_and_withdrawn_cannot_win():
    seats = {A: seat(), B: seat(1), C: seat(0)}
    game = game_of(
        make_round(shooting(True, False), seats=seats),
        settings=Settings(rounds=3),
        results=(RoundResult(A, C), RoundResult(A, C)),
        presence={
            A: Presence.PRESENT,
            B: Presence.PRESENT,
            C: Presence.WITHDRAWN,
        },
    )
    game, events = fire(game, A, Shoot(0, B))
    assert isinstance(game, Finished)
    assert events[-1] == GameFinished((A,))


def test_shield_lasts_through_the_next_turn_only():
    seats = {A: seat(3, Shield(1)), B: seat(), C: seat()}
    game = game_of(make_round(shooting(), seats=seats))
    game = end_turn(game)
    assert game.round.seats[A].effects == (Shield(1),)
    game = end_turn(game)
    assert game.round.seats[A].effects == ()


def test_named_target_lasts_until_its_owner_has_moved():
    on_self = PlayAlong(1, B)
    on_c = PlayAlong(1, A)
    seats = {A: seat(3, on_self), B: seat(), C: seat(3, on_c)}
    game = game_of(make_round(shooting(), seats=seats))
    game = end_turn(game)  # ход A: наложено в этот ход — ещё не в силе
    assert game.round.seats[A].effects == (on_self,)
    game = end_turn(game)  # ход B
    game = end_turn(game)  # ход C: его принуждение отработало
    assert game.round.seats[C].effects == ()
    game = end_turn(game)  # снова A
    assert game.round.seats[A].effects == ()


def test_row_ending_mid_turn_keeps_the_turn():
    seats = {A: seat(3, Double(1)), B: seat(), C: seat()}
    game = game_of(make_round(shooting(False), seats=seats))
    game, events = fire(game, A, Shoot(0, B))
    assert SpreadEnded() in events
    assert isinstance(game.round.spread, Preparing)
    assert (game.round.active, game.round.turn) == (A, 1)
    assert not any(isinstance(e, TurnPassed) for e in events)
