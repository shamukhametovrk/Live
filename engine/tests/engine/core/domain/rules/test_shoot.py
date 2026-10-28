from dataclasses import replace

import pytest

from engine.core.domain.commands import Shoot
from engine.core.domain.errors import IllegalAction
from engine.core.domain.events import ChipEarned, EffectRemoved, Shot
from engine.core.domain.rules.shoot import shoot
from engine.core.domain.state import (
    Double,
    FullForce,
    PlayAlong,
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


def test_hit_takes_one_life_and_ends_turn():
    r, events, ends = shoot(make_round(shooting(True, False)), A, Shoot(0, B))
    assert r.seats[B].health == 2
    assert r.spread.chambers[0].used
    assert events == [Shot(A, 0, B, True, 1)]
    assert ends


def test_full_force_doubles_and_shield_absorbs_both_burn():
    seats = {A: seat(3, FullForce(1)), B: seat(3, Shield(1)), C: seat()}
    r, events, _ = shoot(
        make_round(shooting(True), seats=seats), A, Shoot(0, B)
    )
    assert r.seats[B].health == 3
    assert r.seats[A].effects == r.seats[B].effects == ()
    assert events[0].damage == 0


def test_full_force_alone_takes_two():
    seats = {A: seat(3, FullForce(1)), B: seat(), C: seat()}
    r, _, _ = shoot(make_round(shooting(True), seats=seats), A, Shoot(0, B))
    assert r.seats[B].health == 1
    assert r.seats[A].effects == ()


def test_shield_survives_a_blank():
    seats = {A: seat(), B: seat(3, Shield(1)), C: seat()}
    r, _, _ = shoot(make_round(shooting(False), seats=seats), A, Shoot(0, B))
    assert r.seats[B].effects == (Shield(1),)


@pytest.mark.parametrize(
    ("loaded", "earned"),
    [((False, True), True), ((False, False), False)],
    ids=["cartridge left", "no cartridge left"],
)
def test_blank_at_self_earns_chip_only_if_cartridges_remain(loaded, earned):
    r, events, _ = shoot(make_round(shooting(*loaded)), A, Shoot(0, A))
    assert r.seats[A].chips == int(earned)
    assert (ChipEarned(A) in events) is earned


def test_double_keeps_turn_once():
    seats = {A: seat(3, Double(1)), B: seat(), C: seat()}
    r, events, ends = shoot(
        make_round(shooting(False, False), seats=seats), A, Shoot(0, B)
    )
    assert not ends
    assert EffectRemoved(A, Double(1)) in events
    _, _, ends = shoot(r, A, Shoot(1, B))
    assert ends


def test_named_target_binds_only_from_next_turn():
    seats = {A: seat(3, PlayAlong(1, C)), B: seat(), C: seat()}
    same_turn = make_round(shooting(False, False), seats=seats, turn=1)
    shoot(same_turn, A, Shoot(0, B))
    with pytest.raises(IllegalAction, match="must_shoot_named_target"):
        shoot(replace(same_turn, turn=2), A, Shoot(0, B))


def test_named_chamber_binds_and_using_it_frees_everyone():
    seats = {A: seat(3, TryThis(1, 1)), B: seat(3, TryThis(1, 1)), C: seat()}
    r = make_round(shooting(False, False), seats=seats, turn=2)
    with pytest.raises(IllegalAction, match="must_use_named_chamber"):
        shoot(r, A, Shoot(0, B))
    r, _, _ = shoot(r, A, Shoot(1, B))
    assert r.seats[A].effects == r.seats[B].effects == ()


@pytest.mark.parametrize(
    ("cmd", "code"),
    [
        (Shoot(0, B), "chamber_used"),
        (Shoot(5, B), "no_such_chamber"),
        (Shoot(1, C), "target_not_alive"),
    ],
)
def test_illegal_shots(cmd, code):
    spread = shooting(True, False)
    spread = replace(
        spread,
        chambers=(replace(spread.chambers[0], used=True), spread.chambers[1]),
    )
    seats = {A: seat(), B: seat(), C: seat(0)}
    with pytest.raises(IllegalAction, match=code):
        shoot(make_round(spread, seats=seats), A, cmd)


def test_only_active_player_shoots():
    with pytest.raises(IllegalAction, match="not_your_turn"):
        shoot(make_round(shooting(True)), B, Shoot(0, A))
