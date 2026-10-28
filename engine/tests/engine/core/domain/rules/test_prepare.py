from random import Random

import pytest

from engine.core.domain import parameters
from engine.core.domain.catalog import Item
from engine.core.domain.commands import Prepare
from engine.core.domain.errors import IllegalAction
from engine.core.domain.events import Loaded, Prepared
from engine.core.domain.rules.prepare import deal, prepare
from engine.core.domain.state import Choice, Settings, Shooting
from tests.engine.core.domain.rules.helpers import (
    A,
    B,
    C,
    make_round,
    preparing,
    seat,
)

SETTINGS = Settings()


def test_deal_offers_only_items_in_game():
    only = frozenset(Item) - {Item.SHIELD}
    for s in range(50):
        spread, _ = deal(Settings(excluded=only), (A, B), Random(s))
        assert all(i is Item.SHIELD for o in spread.offers.values() for i in o)
        assert parameters.CHAMBERS[0] <= spread.size <= parameters.CHAMBERS[1]


def test_deal_with_every_item_excluded_offers_nothing():
    spread, _ = deal(Settings(excluded=frozenset(Item)), (A, B), Random(0))
    assert spread.offers == {A: (), B: ()}


def test_hand_is_built_from_old_and_offered_items_counting_repeats():
    seats = {A: seat(3, hand=(Item.WATER,)), B: seat(), C: seat()}
    spread = preparing(4, {A: (Item.WATER, Item.PASS), B: (), C: ()})
    r = make_round(spread, seats=seats)
    prepare(
        SETTINGS, r, A, Prepare((Item.WATER, Item.WATER), (0,) * 4), Random(0)
    )
    with pytest.raises(IllegalAction, match="hand_not_available"):
        prepare(
            SETTINGS, r, A, Prepare((Item.PASS, Item.PASS), (0,) * 4), Random(0)
        )


def test_hand_limit():
    offers = {A: (Item.WATER,) * (parameters.HAND_LIMIT + 1), B: (), C: ()}
    r = make_round(preparing(4, offers))
    with pytest.raises(IllegalAction, match="hand_over_limit"):
        prepare(SETTINGS, r, A, Prepare(offers[A], (0,) * 4), Random(0))


@pytest.mark.parametrize(
    "chips",
    [(1, 0, 0), (1, 0, 0, 0, 0), (0, 0, 0, 1), (-1, 3, 0, 0)],
    ids=["too few chambers", "too many chambers", "not all chips", "negative"],
)
def test_all_earned_chips_go_on_existing_chambers(chips):
    seats = {A: seat(3, chips=2), B: seat(), C: seat()}
    r = make_round(preparing(4), seats=seats)
    with pytest.raises(IllegalAction, match="bad_chips"):
        prepare(SETTINGS, r, A, Prepare((), chips), Random(0))


def test_loads_when_every_living_player_decided():
    seats = {A: seat(3, chips=2), B: seat(), C: seat(0)}
    r = make_round(preparing(4, {A: (Item.PASS,), B: (), C: ()}), seats=seats)
    r, events = prepare(
        SETTINGS, r, A, Prepare((Item.PASS,), (2, 0, 0, 0)), Random(0)
    )
    assert events == [Prepared(A)]
    with pytest.raises(IllegalAction, match="already_prepared"):
        prepare(SETTINGS, r, A, Prepare((), (2, 0, 0, 0)), Random(0))

    r, events = prepare(SETTINGS, r, B, Prepare((), (0,) * 4), Random(0))
    assert isinstance(r.spread, Shooting)
    assert r.seats[A].hand == (Item.PASS,) and r.seats[A].chips == 0
    assert r.spread.weights == (3, 1, 1, 1)
    loaded = events[-1]
    assert isinstance(loaded, Loaded)
    assert sum(loaded.loaded) == loaded.announced <= 3


def test_withdrawn_players_sent_chips_still_count():
    seats = {A: seat(), B: seat(), C: seat(0)}
    spread = preparing(4)
    spread = spread.__class__(
        spread.size, spread.offers, frozendict({C: Choice((), (0, 5, 0, 0))})
    )
    r = make_round(spread, seats=seats)
    r, _ = prepare(SETTINGS, r, A, Prepare((), (0,) * 4), Random(0))
    r, _ = prepare(SETTINGS, r, B, Prepare((), (0,) * 4), Random(0))
    assert r.spread.weights == (1, 6, 1, 1)


def test_cartridges_never_fill_the_whole_row():
    r = make_round(preparing(4), seats={A: seat(), B: seat()})
    settings = Settings(cartridges=(3, 11))
    r, _ = prepare(settings, r, A, Prepare((), (0,) * 4), Random(0))
    r, _ = prepare(settings, r, B, Prepare((), (0,) * 4), Random(0))
    assert r.spread.announced == 3
