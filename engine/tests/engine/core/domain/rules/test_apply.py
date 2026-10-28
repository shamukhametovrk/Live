from collections import Counter
from dataclasses import replace
from random import Random

import pytest

from engine.core.domain.catalog import Item
from engine.core.domain.commands import Take, UseItem
from engine.core.domain.errors import IllegalAction
from engine.core.domain.events import (
    CartridgeRemoved,
    EffectAdded,
    ItemStolen,
    Wasted,
    WeightSeen,
)
from engine.core.domain.rules.apply import apply
from engine.core.domain.state import Chamber, Shield, Shooting, TryThis
from tests.engine.core.domain.rules.helpers import (
    A,
    B,
    C,
    make_round,
    seat,
    shooting,
)


def with_hand(*items, spread=None, health=3, others=None):
    """Раунд, где у A в руке `items`; места B и C можно заменить."""
    spread = spread or shooting(True, False, False)
    seats = {A: seat(health, hand=items), B: seat(), C: seat()}
    seats.update(others or {})
    return make_round(spread, seats=seats)


def use(r, cmd, seed=0):
    return apply(r, A, cmd, Random(seed))


@pytest.mark.parametrize(
    ("cmd", "code"),
    [
        (UseItem(Item.WATER), "item_not_in_hand"),
        (UseItem(Item.REVERSE), "bad_fields"),
        (UseItem(Item.PEEK, chamber=0, player=B), "bad_fields"),
        (UseItem(Item.SHARE, player=A, take=Take.CHIP), "must_name_opponent"),
        (UseItem(Item.TRY_THIS, player=C, chamber=1), "player_not_alive"),
        (UseItem(Item.PEEK, chamber=0), "chamber_used"),
    ],
)
def test_illegal_use_keeps_the_item(cmd, code):
    spread = shooting(True, False)
    spread = replace(
        spread, chambers=(Chamber(True, used=True), Chamber(False))
    )
    r = with_hand(
        Item.REVERSE,
        Item.PEEK,
        Item.SHARE,
        Item.TRY_THIS,
        spread=spread,
        others={C: seat(0)},
    )
    with pytest.raises(IllegalAction, match=code):
        use(r, cmd)


def test_wasted_item_still_leaves_the_hand():
    r, events, _ = use(with_hand(Item.WATER), UseItem(Item.WATER))
    assert events == [Wasted(A, Item.WATER)]
    assert r.seats[A].hand == ()


def test_scared_odds_follow_inverse_weights():
    spread = Shooting(
        chambers=(Chamber(True), Chamber(True), Chamber(True)),
        chips=frozendict({B: (0, 1, 3)}),
        announced=3,
    )
    hits = Counter()
    for s in range(4000):
        _, events, _ = use(
            with_hand(Item.SCARED, spread=spread), UseItem(Item.SCARED), s
        )
        (removed,) = [e for e in events if isinstance(e, CartridgeRemoved)]
        hits[removed.chamber] += 1
    # веса 1, 2, 4 → обратные 4, 3, 1 → 50%, 37,5%, 12,5%
    assert hits[0] / 4000 == pytest.approx(0.5, abs=0.03)
    assert hits[1] / 4000 == pytest.approx(0.375, abs=0.03)
    assert hits[2] / 4000 == pytest.approx(0.125, abs=0.03)


@pytest.mark.parametrize(
    ("item", "loaded", "wasted"),
    [
        (Item.MORE, (True, True), True),
        (Item.MORE, (True, False), False),
        (Item.SCARED, (False, False), True),
        (Item.SHAKE, (False, False), True),
    ],
)
def test_cartridge_items_waste_when_nothing_to_change(item, loaded, wasted):
    _, events, _ = use(with_hand(item, spread=shooting(*loaded)), UseItem(item))
    assert (events == [Wasted(A, item)]) is wasted


def test_shake_moves_cartridges_only_among_unused_chambers():
    spread = shooting(True, True, False, False, False)
    spread = replace(
        spread, chambers=(Chamber(True, used=True), *spread.chambers[1:])
    )
    for s in range(30):
        r, _, _ = use(
            with_hand(Item.SHAKE, spread=spread), UseItem(Item.SHAKE), s
        )
        assert r.spread.chambers[0] == Chamber(True, used=True)
        assert sum(c.loaded for c in r.spread.chambers[1:]) == 1


def test_peek_uses_chamber_without_ending_turn_and_frees_named_chamber():
    r = with_hand(Item.PEEK, others={B: seat(3, TryThis(1, 0))})
    r, _, ends = use(r, UseItem(Item.PEEK, chamber=0))
    assert r.spread.chambers[0].used
    assert r.seats[B].effects == ()
    assert not ends


def test_healing_stops_at_round_start_health():
    r, _, _ = use(with_hand(Item.LIKE_NEW, health=1), UseItem(Item.LIKE_NEW))
    assert r.seats[A].health == 3
    for s in range(20):
        r = with_hand(Item.DUBIOUS, health=2)
        r, _, _ = use(r, UseItem(Item.DUBIOUS), s)
        assert r.seats[A].health in (1, 3)


def test_pass_ends_turn():
    _, _, ends = use(with_hand(Item.PASS), UseItem(Item.PASS))
    assert ends


def test_same_effect_twice_is_wasted_even_on_another_chamber():
    r = with_hand(Item.TRY_THIS, others={B: seat(3, TryThis(1, 1))})
    _, events, _ = use(r, UseItem(Item.TRY_THIS, player=B, chamber=2))
    assert events == [Wasted(A, Item.TRY_THIS)]
    r = with_hand(Item.SHIELD)
    _, events, _ = use(r, UseItem(Item.SHIELD))
    assert events == [EffectAdded(A, Shield(1))]


def test_share_takes_item_into_hand_but_drawing_share_backfires():
    r = with_hand(Item.SHARE, others={B: seat(3, hand=(Item.WATER,))})
    r2, events, _ = use(r, UseItem(Item.SHARE, player=B, take=Take.ITEM))
    assert events == [ItemStolen(A, B, Item.WATER)]
    assert r2.seats[A].hand == (Item.WATER,) and r2.seats[B].hand == ()

    r = with_hand(Item.SHARE, others={B: seat(3, hand=(Item.SHARE,))})
    r2, events, _ = use(r, UseItem(Item.SHARE, player=B, take=Take.ITEM))
    assert events == [Wasted(A, Item.SHARE)]
    assert r2.seats[B].hand == (Item.SHARE,)


def test_one_eye_reveals_weight_to_its_user():
    spread = replace(shooting(True, False), chips=frozendict({B: (2, 0)}))
    r, events, _ = use(
        with_hand(Item.ONE_EYE, spread=spread), UseItem(Item.ONE_EYE, chamber=0)
    )
    assert events == [WeightSeen(A, 0, 3)]
    assert r.spread.revealed == {A: {0}}
