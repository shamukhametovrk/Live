"""Начало ряда (см. правила домена, «Начало ряда»)."""

from collections import Counter
from dataclasses import replace
from random import Random

from engine.libs.weighted_subset_sampler import sample_weighted_mask

from .. import parameters
from ..catalog import CATALOG, Item
from ..commands import Prepare
from ..errors import IllegalAction
from ..events import Event, Loaded, Prepared, SpreadStarted
from ..ids import PlayerID
from ..state import Chamber, Choice, Preparing, Round, Settings, Shooting


def deal(
    settings: Settings, players: tuple[PlayerID, ...], rng: Random
) -> tuple[Preparing, list[Event]]:
    """Число камор и выдача для живых `players`."""
    size = rng.randint(*settings.chambers)
    pools = {
        cls: [
            i
            for i in Item
            if CATALOG[i].cls is cls and i not in settings.excluded
        ]
        for cls in parameters.DEAL_CLASS_ODDS
    }
    pools = {cls: items for cls, items in pools.items() if items}
    count = rng.randint(*parameters.DEAL_SIZE)
    classes = (
        rng.choices(
            list(pools),
            weights=[parameters.DEAL_CLASS_ODDS[c] for c in pools],
            k=count,
        )
        if pools
        else []
    )
    offers = frozendict(
        {p: tuple(rng.choice(pools[c]) for c in classes) for p in players}
    )
    return Preparing(size, offers), [SpreadStarted(size, offers)]


def prepare(
    settings: Settings,
    round_: Round,
    actor: PlayerID,
    cmd: Prepare,
    rng: Random,
) -> tuple[Round, list[Event]]:
    spread = round_.spread
    if not isinstance(spread, Preparing):
        raise IllegalAction("not_preparing")
    seat = round_.seats.get(actor)
    if seat is None or not seat.alive:
        raise IllegalAction("not_alive")
    if actor in spread.choices:
        raise IllegalAction("already_prepared")
    if not Counter(cmd.hand) <= Counter(seat.hand + spread.offers[actor]):
        raise IllegalAction("hand_not_available")
    if len(cmd.hand) > parameters.HAND_LIMIT:
        raise IllegalAction("hand_over_limit")
    if (
        len(cmd.chips) != spread.size
        or any(c < 0 for c in cmd.chips)
        or sum(cmd.chips) != seat.chips
    ):
        raise IllegalAction("bad_chips")
    # - - -
    choices = spread.choices | {actor: Choice(cmd.hand, cmd.chips)}
    round_ = replace(round_, spread=replace(spread, choices=choices))
    round_, loaded = load_if_ready(settings, round_, rng)
    return round_, [Prepared(actor), *loaded]


def load_if_ready(
    settings: Settings, round_: Round, rng: Random
) -> tuple[Round, list[Event]]:
    """Заряжает ряд, если решение есть у каждого живого."""
    spread = round_.spread
    assert isinstance(spread, Preparing)
    if any(p not in spread.choices for p in round_.alive):
        return round_, []
    # Решение выбывшего, если он успел его отправить, тоже учитывается.
    choices = spread.choices
    seats = round_.seats | {
        p: replace(round_.seats[p], hand=c.hand, chips=0)
        for p, c in choices.items()
    }
    chips = frozendict({p: c.chips for p, c in choices.items()})
    low, high = settings.cartridges
    count = rng.randint(low, min(high, spread.size - 1))
    weights = [
        1 + sum(c[i] for c in chips.values()) for i in range(spread.size)
    ]
    mask = tuple(sample_weighted_mask(weights, count, rng))
    shooting = Shooting(tuple(Chamber(m) for m in mask), chips, count)
    event = Loaded(
        offers=spread.offers,
        hands=frozendict({p: c.hand for p, c in choices.items()}),
        chips=chips,
        loaded=mask,
        announced=count,
    )
    return replace(round_, seats=seats, spread=shooting), [event]
