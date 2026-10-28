from dataclasses import replace
from random import Random

import pytest

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
from engine.core.domain.rules.effects import expired
from engine.core.domain.rules.settle import settle
from engine.core.domain.rules.shoot import shoot
from engine.core.domain.state import (
    Double,
    Finished,
    FullForce,
    InProgress,
    PlayAlong,
    Preparing,
    Presence,
    Round,
    RoundResult,
    Settings,
    Shield,
    TryThis,
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


@pytest.mark.parametrize(
    ("effect", "ended_turn", "ended_active", "gone"),
    [
        (Double(1), 1, A, True),
        (FullForce(1), 5, A, False),
        (Shield(1), 1, A, False),
        (Shield(1), 2, B, True),
        (PlayAlong(1, B), 1, A, False),  # на себя в свой ход — ещё не в силе
        (PlayAlong(1, B), 2, B, False),  # чужой ход не в счёт
        (PlayAlong(1, B), 4, A, True),  # отработал свой следующий ход
        (TryThis(1, 0), 3, C, False),
    ],
)
def test_effect_lifetimes(effect, ended_turn, ended_active, gone):
    """Сроки эффектов; владелец — A."""
    assert expired(effect, A, ended_turn, ended_active) is gone


def test_dying_on_own_turn_ends_it_even_with_double():
    seats = {A: seat(1, Double(1)), B: seat(), C: seat()}
    game = game_of(make_round(shooting(True, False), seats=seats))
    game, events = fire(game, A, Shoot(0, A))
    assert events[-1] == TurnPassed(B, 2)


def test_row_ending_mid_turn_keeps_the_turn():
    seats = {A: seat(3, Double(1)), B: seat(), C: seat()}
    game = game_of(make_round(shooting(False), seats=seats))
    game, events = fire(game, A, Shoot(0, B))
    assert SpreadEnded() in events
    assert isinstance(game.round.spread, Preparing)
    assert (game.round.active, game.round.turn) == (A, 1)
    assert not any(isinstance(e, TurnPassed) for e in events)
