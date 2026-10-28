"""Выстрел (см. правила домена, «Выстрел»).

Гибель, конец хода и ряда разбирает не выстрел, а разбор последствий;
выстрел только говорит, закончил ли он ход.
"""

from dataclasses import replace

from ..commands import Shoot
from ..errors import IllegalAction
from ..events import ChipEarned, EffectRemoved, Event, Shot
from ..ids import PlayerID
from ..state import (
    Chamber,
    Double,
    Effect,
    FullForce,
    PlayAlong,
    Round,
    Shield,
    Shooting,
    TryThis,
)
from .effects import find, in_force, without


def shoot(
    round_: Round, actor: PlayerID, cmd: Shoot
) -> tuple[Round, list[Event], bool]:
    """Новый раунд, события и закончил ли выстрел ход."""
    spread = round_.spread
    if not isinstance(spread, Shooting):
        raise IllegalAction("not_shooting")
    if actor != round_.active:
        raise IllegalAction("not_your_turn")
    if not 0 <= cmd.chamber < len(spread.chambers):
        raise IllegalAction("no_such_chamber")
    if spread.chambers[cmd.chamber].used:
        raise IllegalAction("chamber_used")
    target = round_.seats.get(cmd.target)
    if target is None or not target.alive:
        raise IllegalAction("target_not_alive")
    seat = round_.seats[actor]
    named_target = find(seat, PlayAlong)
    if (
        named_target
        and in_force(named_target, round_.turn)
        and cmd.target != named_target.target
    ):
        raise IllegalAction("must_shoot_named_target")
    named_chamber = find(seat, TryThis)
    if (
        named_chamber
        and in_force(named_chamber, round_.turn)
        and cmd.chamber != named_chamber.chamber
    ):
        raise IllegalAction("must_use_named_chamber")
    # - - -
    seats = dict(round_.seats)
    removed: list[tuple[PlayerID, Effect]] = []

    def take(player: PlayerID, effect: Effect | None) -> bool:
        """Снимает эффект, если он есть; говорит, был ли он."""
        if effect is None:
            return False
        seats[player] = without(seats[player], effect)
        removed.append((player, effect))
        return True

    loaded = spread.chambers[cmd.chamber].loaded
    chambers = list(spread.chambers)
    chambers[cmd.chamber] = Chamber(loaded, used=True)
    for player in round_.seats:
        named = find(seats[player], TryThis)
        if named and named.chamber == cmd.chamber:
            take(player, named)

    damage = 0
    earned = False
    if loaded:
        damage = 2 if take(actor, find(seats[actor], FullForce)) else 1
        if take(cmd.target, find(seats[cmd.target], Shield)):
            damage = 0
        hit = seats[cmd.target]
        seats[cmd.target] = replace(hit, health=max(0, hit.health - damage))
    elif cmd.target == actor and any(c.loaded and not c.used for c in chambers):
        earned = True
        seats[actor] = replace(seats[actor], chips=seats[actor].chips + 1)

    ends_turn = not take(actor, find(seats[actor], Double))
    # - - -
    events: list[Event] = [
        Shot(actor, cmd.chamber, cmd.target, loaded, damage),
        *(EffectRemoved(p, e) for p, e in removed),
    ]
    if earned:
        events.append(ChipEarned(actor))
    new_round = replace(
        round_,
        seats=frozendict(seats),
        spread=replace(spread, chambers=tuple(chambers)),
    )
    return new_round, events, ends_turn
