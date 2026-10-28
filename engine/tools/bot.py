"""Простой бот: случайные, но правдоподобные команды.

Им играют сквозные тесты и летопись игры.
"""

from random import Random

from engine.core.domain import parameters
from engine.core.domain.catalog import CATALOG, Field
from engine.core.domain.commands import (
    ChangeSettings,
    Disconnect,
    Join,
    Prepare,
    Reconnect,
    Shoot,
    Start,
    Take,
    Timeout,
    UseItem,
)
from engine.core.domain.ids import PlayerID
from engine.core.domain.state import (
    InProgress,
    Lobby,
    Preparing,
    Presence,
    Settings,
    Shooting,
)


def random_settings(rng: Random) -> Settings:
    def span(low, high):
        a = rng.randint(low, high)
        return a, rng.randint(a, high)

    chambers = span(*parameters.CHAMBERS)
    return Settings(
        rounds=rng.randint(1, 3),
        health=span(*parameters.HEALTH),
        chambers=chambers,
        cartridges=span(1, chambers[0] - 1),
    )


def lobby_command(game: Lobby | None, seats: int, rng: Random):
    if game is None or len(game.players) < seats:
        joined = 0 if game is None else len(game.players)
        return PlayerID(joined + 1), Join()
    if rng.random() < 0.3:
        return game.host, ChangeSettings(random_settings(rng))
    return game.host, Start()


def presence_command(game: Lobby | InProgress, rng: Random):
    away = [p for p, s in game.presence.items() if s is Presence.AWAY]
    if away:
        p = rng.choice(away)
        return None, (Reconnect(p) if rng.random() < 0.7 else Timeout(p))
    present = [p for p, s in game.presence.items() if s is Presence.PRESENT]
    return None, Disconnect(rng.choice(present))


def game_command(game: InProgress, rng: Random):
    round_ = game.round
    spread = round_.spread
    alive = list(round_.alive)
    if isinstance(spread, Preparing):
        p = rng.choice([q for q in alive if q not in spread.choices])
        seat = round_.seats[p]
        pool = list(seat.hand + spread.offers[p])
        hand = rng.sample(pool, rng.randint(0, min(len(pool), 8)))
        chips = [0] * spread.size
        for _ in range(seat.chips):
            chips[rng.randrange(spread.size)] += 1
        return p, Prepare(tuple(hand), tuple(chips))
    assert isinstance(spread, Shooting)
    p = round_.active
    free = [i for i, c in enumerate(spread.chambers) if not c.used]
    hand = round_.seats[p].hand
    if hand and rng.random() < 0.4:
        item = rng.choice(hand)
        fields = CATALOG[item].fields
        return p, UseItem(
            item,
            player=rng.choice(alive) if Field.PLAYER in fields else None,
            target=rng.choice(alive) if Field.TARGET in fields else None,
            chamber=rng.choice(free) if Field.CHAMBER in fields else None,
            take=rng.choice(list(Take)) if Field.TAKE in fields else None,
        )
    return p, Shoot(rng.choice(free), rng.choice(alive))
