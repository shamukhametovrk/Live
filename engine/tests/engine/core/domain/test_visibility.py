"""Скрытое не утекает: ни в снимок, ни в сообщения чужим.

Совпадение снимка и картины мира проверяют сквозные игры; здесь — что
скрытого нет в обоих.
"""

from engine.core.domain import events as e
from engine.core.domain.catalog import Item
from engine.core.domain.state import (
    Chamber,
    InProgress,
    Preparing,
    Presence,
    Settings,
    Shooting,
)
from engine.core.domain.visibility import project, view
from tests.engine.core.domain.rules.helpers import A, B, make_round


def game_of(spread) -> InProgress:
    return InProgress(
        Settings(),
        (A, B),
        frozendict({A: Presence.PRESENT, B: Presence.PRESENT}),
        (),
        make_round(spread),
    )


def test_snapshot_hides_unused_chambers_and_others_chips():
    spread = Shooting(
        chambers=(Chamber(True, used=True), Chamber(True), Chamber(False)),
        chips=frozendict({A: (0, 2, 0), B: (1, 0, 0)}),
        announced=2,
        revealed=frozendict({A: frozenset({1})}),
    )
    shown = view(game_of(spread), A).round.spread
    assert [c.loaded for c in shown.chambers] == [True, None, None]
    assert shown.chips == (0, 2, 0)
    assert shown.seen == {1: 3}


def test_snapshot_shows_only_own_offer():
    spread = Preparing(4, frozendict({A: (Item.PASS,), B: (Item.SHIELD,)}))
    assert view(game_of(spread), B).round.spread.offer == (Item.SHIELD,)


def test_hidden_fields_reach_only_their_owner():
    seen = e.WeightSeen(A, 0, 5)
    assert project(seen, A).weight == 5
    assert project(seen, B).weight is None
    loaded = e.Loaded(
        frozendict(), frozendict(), frozendict({A: (1, 0)}), (True, False), 1
    )
    assert project(loaded, A).chips == (1, 0)
    assert project(loaded, B).chips is None
    assert not hasattr(project(loaded, A), "loaded")
