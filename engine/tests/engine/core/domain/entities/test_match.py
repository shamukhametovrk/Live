"""Инварианты партии `Match`: состав, очередь хода, стадии."""

from collections.abc import Iterable
from random import Random

import pytest

from engine.core.domain.entities import (
    ChamberRow,
    Match,
    Preparation,
    Round,
    Seat,
)
from engine.core.domain.exceptions import DomainError
from engine.core.domain.ids import PlayerID
from engine.core.domain.value_objects import (
    MatchState,
    PreparationState,
    RoundConfig,
    RoundState,
)

A, B, C, D = PlayerID(1), PlayerID(2), PlayerID(3), PlayerID(4)
CIRCLE = (A, B, C, D)
CONFIG = RoundConfig(chambers=4, cartridges=1, layers=(1,))


def make_seats(players: Iterable[PlayerID]) -> dict[PlayerID, Seat]:
    return {p: Seat(max_items=2, health_points=3) for p in players}


def make_preparation(participants: Iterable[PlayerID]) -> Preparation:
    players = set(participants)
    return Preparation(CONFIG, players, {p: () for p in players})


def make_round() -> Round:
    return Round(ChamberRow([1, 1, 1, 1], 0, Random(0)), {}, 0)


def make_match(first: PlayerID = A) -> Match:
    return Match(make_seats(CIRCLE), CIRCLE, first, make_preparation(CIRCLE))


def kill(match: Match, *players: PlayerID) -> None:
    for player in players:
        match.seat(player).health_points = 0


def in_round(match: Match) -> Match:
    match.start_round(make_round())
    return match


# --------------------------------------------------------------------------- #
# Создание
# --------------------------------------------------------------------------- #


def test_new_match_state() -> None:
    match = make_match(first=C)

    assert match.turn_circle == CIRCLE
    assert match.active == C
    assert match.turn_number == 1
    assert match.alive == CIRCLE
    assert not match.in_round


def test_seats_are_stored_by_reference_but_mapping_is_copied() -> None:
    seats = make_seats(CIRCLE)
    match = Match(seats, CIRCLE, A, make_preparation(CIRCLE))
    seats.pop(A)

    assert match.seat(A) is not None
    assert match.seat(B) is seats[B]


def test_turn_circle_accepts_any_sequence() -> None:
    match = Match(make_seats(CIRCLE), list(CIRCLE), A, make_preparation(CIRCLE))
    assert match.turn_circle == CIRCLE


@pytest.mark.parametrize(
    ("players", "circle"),
    [
        ((A,), (A,)),
        ((A, B), (A, A, B)),
        ((A, B, C), (A, B)),
        ((A, B), (A, B, C)),
    ],
    ids=["one-player", "duplicates", "extra-seat", "seat-missing"],
)
def test_bad_circle_is_engine_bug(
    players: tuple[PlayerID, ...], circle: tuple[PlayerID, ...]
) -> None:
    with pytest.raises(ValueError) as info:
        Match(make_seats(players), circle, A, make_preparation(players))
    assert not isinstance(info.value, DomainError)


def test_first_player_outside_match_rejected() -> None:
    with pytest.raises(ValueError):
        Match(
            make_seats(CIRCLE), CIRCLE, PlayerID(99), make_preparation(CIRCLE)
        )


@pytest.mark.parametrize(
    "participants",
    [(A, B, C), (A, B, C, D, PlayerID(99))],
    ids=["someone-missing", "stranger"],
)
def test_preparation_must_cover_exactly_alive_players(
    participants: tuple[PlayerID, ...],
) -> None:
    with pytest.raises(ValueError):
        Match(make_seats(CIRCLE), CIRCLE, A, make_preparation(participants))


# --------------------------------------------------------------------------- #
# Места
# --------------------------------------------------------------------------- #


def test_unknown_seat_is_engine_bug() -> None:
    with pytest.raises(ValueError):
        make_match().seat(PlayerID(99))


def test_alive_keeps_circle_order_and_skips_dead() -> None:
    match = make_match()
    kill(match, B, D)
    assert match.alive == (A, C)


# --------------------------------------------------------------------------- #
# Передача хода
# --------------------------------------------------------------------------- #


def test_pass_turn_goes_around_the_circle() -> None:
    match = make_match(first=C)
    order = []
    for _ in range(5):
        match.pass_turn()
        order.append(match.active)

    assert order == [D, A, B, C, D]
    assert match.turn_number == 6


def test_pass_turn_skips_dead() -> None:
    match = make_match(first=A)
    kill(match, B, C)
    match.pass_turn()
    assert match.active == D


def test_pass_turn_from_dead_active_goes_to_next_alive_after_him() -> None:
    match = make_match(first=B)
    kill(match, B)
    match.pass_turn()
    assert match.active == C


def test_single_alive_active_keeps_the_turn() -> None:
    match = make_match(first=A)
    kill(match, B, C, D)
    match.pass_turn()

    assert match.active == A
    assert match.turn_number == 2


def test_single_alive_other_gets_the_turn() -> None:
    match = make_match(first=A)
    kill(match, A, B, D)
    match.pass_turn()
    assert match.active == C


def test_pass_turn_without_alive_is_engine_bug_and_unchanged() -> None:
    match = make_match(first=B)
    kill(match, *CIRCLE)

    with pytest.raises(ValueError):
        match.pass_turn()
    assert match.active == B
    assert match.turn_number == 1


# --------------------------------------------------------------------------- #
# Стадии
# --------------------------------------------------------------------------- #


def test_preparation_stage_accessors() -> None:
    match = make_match()
    preparation = match.preparation

    assert preparation.participants == frozenset(CIRCLE)
    with pytest.raises(ValueError):
        _ = match.round


def test_start_round_switches_stage() -> None:
    match = make_match()
    round_ = make_round()
    match.start_round(round_)

    assert match.in_round
    assert match.round is round_
    with pytest.raises(ValueError):
        _ = match.preparation


def test_start_round_twice_is_engine_bug() -> None:
    match = in_round(make_match())
    with pytest.raises(ValueError):
        match.start_round(make_round())


def test_start_preparation_during_preparation_is_engine_bug() -> None:
    match = make_match()
    with pytest.raises(ValueError):
        match.start_preparation(make_preparation(CIRCLE))


def test_start_preparation_for_alive_players() -> None:
    match = in_round(make_match())
    kill(match, C)
    preparation = make_preparation((A, B, D))
    match.start_preparation(preparation)

    assert not match.in_round
    assert match.preparation is preparation


def test_start_preparation_with_dead_participant_rejected() -> None:
    match = in_round(make_match())
    kill(match, C)

    with pytest.raises(ValueError):
        match.start_preparation(make_preparation(CIRCLE))
    assert match.in_round


def test_stage_changes_keep_the_turn() -> None:
    match = make_match(first=B)
    match.pass_turn()
    in_round(match)
    match.start_preparation(make_preparation(CIRCLE))

    assert match.active == C
    assert match.turn_number == 2


# --------------------------------------------------------------------------- #
# Снимок
# --------------------------------------------------------------------------- #


def test_state_in_preparation() -> None:
    match = make_match(first=B)
    kill(match, D)

    state = match.state
    assert isinstance(state, MatchState)
    assert state.turn_circle == CIRCLE
    assert state.active == B
    assert state.turn_number == 1
    assert state.seats[D].health_points == 0
    assert set(state.seats) == set(CIRCLE)
    assert isinstance(state.stage, PreparationState)


def test_state_in_round() -> None:
    match = in_round(make_match())
    assert isinstance(match.state.stage, RoundState)


def test_state_is_detached_from_later_changes() -> None:
    match = make_match()
    snapshot = match.state
    match.pass_turn()
    kill(match, C)

    assert snapshot.active == A
    assert snapshot.turn_number == 1
    assert snapshot.seats[C].health_points == 3
