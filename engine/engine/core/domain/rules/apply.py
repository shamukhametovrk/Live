"""Применение предмета (см. правила домена, «Применение предмета»).

Общие проверки здесь, дальше — ветка предмета. Гибель, конец хода и
ряда разбирает разбор последствий; применение только говорит, закончило
ли оно ход.
"""

from dataclasses import dataclass, replace
from random import Random
from typing import assert_never

from engine.libs.weighted_subset_sampler import (
    sample_weighted_mask,
    sample_weighted_subset,
)

from ..catalog import CATALOG, Field, Item
from ..commands import Take, UseItem
from ..errors import IllegalAction
from ..events import (
    CartridgeAdded,
    CartridgeRemoved,
    ChipStolen,
    EffectAdded,
    EffectRemoved,
    Event,
    Gambled,
    Healed,
    ItemStolen,
    Jackpot,
    Passed,
    Peeked,
    Reversed,
    Shaken,
    Wasted,
    WeightSeen,
    WeightsSeen,
)
from ..ids import PlayerID
from ..state import (
    Chamber,
    Double,
    Effect,
    FullForce,
    PlayAlong,
    Round,
    Seat,
    Shield,
    Shooting,
    TryThis,
)
from .chambers import use_chamber
from .effects import find


class _Wasted(Exception):
    """Предмету не на чем сработать."""


@dataclass
class _Table:
    """Изменяемая копия того, что могут тронуть предметы."""

    seats: dict[PlayerID, Seat]
    chambers: list[Chamber]
    revealed: dict[PlayerID, frozenset[int]]
    weights: tuple[int, ...]
    start_health: int
    turn: int


def apply(
    round_: Round, actor: PlayerID, cmd: UseItem, rng: Random
) -> tuple[Round, list[Event], bool]:
    """Новый раунд, события и закончило ли применение ход."""
    spread = round_.spread
    _check(round_, actor, cmd)
    assert isinstance(spread, Shooting)
    # - - -
    seats = dict(round_.seats)
    hand = list(seats[actor].hand)
    hand.remove(cmd.item)
    seats[actor] = replace(seats[actor], hand=tuple(hand))
    table = _Table(
        seats=dict(seats),
        chambers=list(spread.chambers),
        revealed=dict(spread.revealed),
        weights=spread.weights,
        start_health=round_.start_health,
        turn=round_.turn,
    )
    try:
        events = _use(table, actor, cmd, rng)
    except _Wasted:
        events = [Wasted(actor, cmd.item)]
        table.seats, table.chambers = seats, list(spread.chambers)
        table.revealed = dict(spread.revealed)
    new_round = replace(
        round_,
        seats=frozendict(table.seats),
        spread=replace(
            spread,
            chambers=tuple(table.chambers),
            revealed=frozendict(table.revealed),
        ),
    )
    ends_turn = cmd.item is Item.PASS
    return new_round, events, ends_turn


def _check(round_: Round, actor: PlayerID, cmd: UseItem) -> None:
    spread = round_.spread
    if not isinstance(spread, Shooting):
        raise IllegalAction("not_shooting")
    if actor != round_.active:
        raise IllegalAction("not_your_turn")
    if cmd.item not in round_.seats[actor].hand:
        raise IllegalAction("item_not_in_hand")
    given = {
        f
        for f, value in (
            (Field.PLAYER, cmd.player),
            (Field.TARGET, cmd.target),
            (Field.CHAMBER, cmd.chamber),
            (Field.TAKE, cmd.take),
        )
        if value is not None
    }
    if given != CATALOG[cmd.item].fields:
        raise IllegalAction("bad_fields")
    for player in (cmd.player, cmd.target):
        if player is not None:
            seat = round_.seats.get(player)
            if seat is None or not seat.alive:
                raise IllegalAction("player_not_alive")
    if cmd.chamber is not None:
        if not 0 <= cmd.chamber < len(spread.chambers):
            raise IllegalAction("no_such_chamber")
        if spread.chambers[cmd.chamber].used:
            raise IllegalAction("chamber_used")
    if cmd.item is Item.SHARE and cmd.player == actor:
        raise IllegalAction("must_name_opponent")


def _use(t: _Table, actor: PlayerID, cmd: UseItem, rng: Random) -> list[Event]:
    me = t.seats[actor]
    match cmd.item:
        case Item.ONE_EYE:
            i = _given(cmd.chamber)
            t.revealed[actor] = t.revealed.get(actor, frozenset()) | {i}
            return [WeightSeen(actor, i, t.weights[i])]
        case Item.WIDE_EYES:
            t.revealed[actor] = frozenset(range(len(t.chambers)))
            return [WeightsSeen(actor, t.weights)]
        case Item.REVERSE:
            i = _given(cmd.chamber)
            t.chambers[i] = Chamber(not t.chambers[i].loaded)
            return [Reversed(actor, i, t.chambers[i].loaded)]
        case Item.MORE:
            spots = [
                i
                for i, c in enumerate(t.chambers)
                if not c.used and not c.loaded
            ]
            i = _pick(spots, [t.weights[i] for i in spots], rng)
            t.chambers[i] = Chamber(True)
            return [CartridgeAdded(actor, i)]
        case Item.SCARED:
            spots = [
                i for i, c in enumerate(t.chambers) if not c.used and c.loaded
            ]
            top = max(t.weights) + 1
            i = _pick(spots, [top - t.weights[i] for i in spots], rng)
            t.chambers[i] = Chamber(False)
            return [CartridgeRemoved(actor, i)]
        case Item.PEEK:
            i = _given(cmd.chamber)
            removed = use_chamber(t.seats, t.chambers, i)
            return [
                Peeked(actor, i, t.chambers[i].loaded),
                *(EffectRemoved(p, e) for p, e in removed),
            ]
        case Item.SHAKE:
            spots = [i for i, c in enumerate(t.chambers) if not c.used]
            count = sum(t.chambers[i].loaded for i in spots)
            if count == 0:
                raise _Wasted
            mask = sample_weighted_mask(
                [t.weights[i] for i in spots], count, rng
            )
            for i, loaded in zip(spots, mask, strict=True):
                t.chambers[i] = Chamber(loaded)
            return [Shaken(actor, tuple(c.loaded for c in t.chambers))]
        case Item.WATER:
            amount = _heal(t, actor, 1)
            return [Healed(actor, cmd.item, amount)]
        case Item.LIKE_NEW:
            amount = _heal(t, actor, t.start_health)
            return [Healed(actor, cmd.item, amount)]
        case Item.DUBIOUS:
            won = rng.random() < 0.5
            amount = min(2, t.start_health - me.health) if won else -1
            t.seats[actor] = replace(me, health=me.health + amount)
            return [Gambled(actor, won, amount)]
        case Item.PASS:
            return [Passed(actor)]
        case Item.DOUBLE:
            return _add_effect(t, actor, Double(t.turn))
        case Item.FULL_FORCE:
            return _add_effect(t, actor, FullForce(t.turn))
        case Item.SHIELD:
            return _add_effect(t, actor, Shield(t.turn))
        case Item.TRY_THIS:
            effect = TryThis(t.turn, _given(cmd.chamber))
            return _add_effect(t, _given(cmd.player), effect)
        case Item.PLAY_ALONG:
            effect = PlayAlong(t.turn, _given(cmd.target))
            return _add_effect(t, _given(cmd.player), effect)
        case Item.SHARE:
            return _share(t, actor, _given(cmd.player), _given(cmd.take), rng)
        case Item.JACKPOT:
            t.seats[actor] = replace(me, chips=me.chips + 3)
            return [Jackpot(actor)]
        case _:
            assert_never(cmd.item)


def _given[T](value: T | None) -> T:
    """Поле, наличие которого уже проверено по справочнику."""
    assert value is not None
    return value


def _pick(spots: list[int], weights: list[int], rng: Random) -> int:
    if not spots:
        raise _Wasted
    (k,) = sample_weighted_subset(weights, 1, rng)
    return spots[k]


def _heal(t: _Table, actor: PlayerID, amount: int) -> int:
    seat = t.seats[actor]
    amount = min(amount, t.start_health - seat.health)
    if amount <= 0:
        raise _Wasted
    t.seats[actor] = replace(seat, health=seat.health + amount)
    return amount


def _add_effect(t: _Table, owner: PlayerID, effect: Effect) -> list[Event]:
    seat = t.seats[owner]
    if find(seat, type(effect)):
        raise _Wasted
    t.seats[owner] = replace(seat, effects=(*seat.effects, effect))
    return [EffectAdded(owner, effect)]


def _share(
    t: _Table, actor: PlayerID, victim: PlayerID, take: Take, rng: Random
) -> list[Event]:
    me, them = t.seats[actor], t.seats[victim]
    match take:
        case Take.ITEM:
            if not them.hand:
                raise _Wasted
            item = rng.choice(them.hand)
            if item is Item.SHARE:
                raise _Wasted
            rest = list(them.hand)
            rest.remove(item)
            t.seats[victim] = replace(them, hand=tuple(rest))
            t.seats[actor] = replace(me, hand=(*me.hand, item))
            return [ItemStolen(actor, victim, item)]
        case Take.CHIP:
            if them.chips == 0:
                raise _Wasted
            t.seats[victim] = replace(them, chips=them.chips - 1)
            t.seats[actor] = replace(me, chips=me.chips + 1)
            return [ChipStolen(actor, victim)]
        case _:
            assert_never(take)
