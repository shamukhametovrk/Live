"""Сквозные игры: случайные игроки от первого Join до конца игры.

Бот шлёт случайные, иногда недопустимые команды через вход в домен,
теряет связь и выбывает. После каждого шага проверяются инварианты.
"""

from random import Random

import pytest

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
from engine.core.domain.errors import IllegalAction
from engine.core.domain.events import RoundStarted, SpreadStarted
from engine.core.domain.ids import PlayerID
from engine.core.domain.rules.handle import handle
from engine.core.domain.state import (
    Finished,
    InProgress,
    Lobby,
    Preparing,
    Presence,
    Settings,
    Shooting,
)

GAMES = 300
MAX_STEPS = 5000


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


def check_invariants(before, after, events) -> None:
    if not isinstance(after, InProgress):
        return
    round_ = after.round
    for p, seat in round_.seats.items():
        assert 0 <= seat.health <= round_.start_health
        assert len(seat.hand) <= parameters.HAND_LIMIT
        kinds = [type(e) for e in seat.effects]
        assert len(kinds) == len(set(kinds))
        if after.presence[p] is Presence.WITHDRAWN:
            assert not seat.alive
    spread = round_.spread
    if isinstance(spread, Shooting):
        assert round_.seats[round_.active].alive
        assert spread.announced < len(spread.chambers)
        fresh = any(
            isinstance(e, (RoundStarted, SpreadStarted)) for e in events
        )
        if (
            isinstance(before, InProgress)
            and isinstance(before.round.spread, Shooting)
            and not fresh
        ):
            for old, new in zip(
                before.round.spread.chambers, spread.chambers, strict=True
            ):
                if old.used:
                    assert new == old


def play(seed: int) -> tuple[object, int]:
    rng = Random(seed)
    seats = rng.randint(*parameters.PLAYERS)
    game = None
    for step in range(MAX_STEPS):
        if isinstance(game, Finished):
            return game, step
        if game is not None and rng.random() < 0.02:
            actor, cmd = presence_command(game, rng)
        elif game is None or isinstance(game, Lobby):
            actor, cmd = lobby_command(game, seats, rng)
        else:
            actor, cmd = game_command(game, rng)
        try:
            outcome = handle(game, actor, cmd, rng)
        except IllegalAction:
            continue
        check_invariants(game, outcome.game, outcome.events)
        game = outcome.game
        if game is None:  # хост ушёл из лобби — начинаем заново
            seats = rng.randint(*parameters.PLAYERS)
    return game, MAX_STEPS


@pytest.mark.parametrize("seed", range(GAMES))
def test_random_game_finishes_keeping_invariants(seed):
    game, steps = play(seed)
    assert isinstance(game, Finished), f"no finish in {steps} steps"


def test_same_seed_same_game():
    assert play(7) == play(7)
