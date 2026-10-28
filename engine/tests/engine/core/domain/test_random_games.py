"""Сквозные игры: случайные игроки от первого Join до конца игры.

Бот шлёт случайные, иногда недопустимые команды через вход в домен,
теряет связь и выбывает, а иногда шлёт мусор: случайную команду с
бессмысленными полями от кого попало. Мусор обязан кончаться отказом
(`IllegalAction`) или нормальным ходом — никогда другим исключением.
После каждого шага проверяются инварианты и
главное правило видимости: снимок + сообщения = снимок. Каждый игрок
держит картину мира (эталон из world.py) — так же, как будет держать клиент.
"""

from random import Random

from engine.core.domain import parameters
from engine.core.domain.catalog import Item
from engine.core.domain.commands import (
    ChangeSettings,
    Disconnect,
    Join,
    Leave,
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
from engine.core.domain.messages import Left
from engine.core.domain.rules.handle import handle
from engine.core.domain.state import (
    Finished,
    InProgress,
    Lobby,
    Presence,
    Settings,
    Shooting,
)
from engine.core.domain.visibility import project, view
from tests.engine.core.domain.world import apply
from tools.bot import game_command, lobby_command, presence_command

GAMES = 300
GARBAGE = 0.1
MAX_STEPS = 5000


def garbage_command(rng: Random):
    """Случайная команда с бессмысленными полями от кого попало."""

    def player():
        return PlayerID(rng.randint(0, 8))

    def maybe(make):
        return make() if rng.random() < 0.5 else None

    def span():
        return rng.randint(-1, 14), rng.randint(-1, 14)

    items = list(Item)
    cmd = rng.choice(
        [
            lambda: Join(),
            lambda: Leave(),
            lambda: Start(),
            lambda: ChangeSettings(
                Settings(
                    rounds=rng.randint(-1, 9),
                    health=span(),
                    chambers=span(),
                    cartridges=span(),
                    excluded=frozenset(rng.sample(items, rng.randint(0, 18))),
                )
            ),
            lambda: Prepare(
                tuple(rng.choices(items, k=rng.randint(0, 10))),
                tuple(rng.randint(-2, 5) for _ in range(rng.randint(0, 14))),
            ),
            lambda: Shoot(rng.randint(-2, 15), player()),
            lambda: UseItem(
                rng.choice(items),
                player=maybe(player),
                target=maybe(player),
                chamber=maybe(lambda: rng.randint(-2, 15)),
                take=maybe(lambda: rng.choice(list(Take))),
            ),
            lambda: Disconnect(player()),
            lambda: Reconnect(player()),
            lambda: Timeout(player()),
        ]
    )()
    return rng.choice([None, player()]), cmd


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


def check_worlds(worlds: dict, game, events) -> None:
    """Картина мира каждого игрока совпадает с его новым снимком."""
    for p in list(worlds):
        for event in events:
            worlds[p] = apply(worlds[p], project(event, p))
        if any(isinstance(ev, Left) and ev.player == p for ev in events):
            del worlds[p]
        elif game is None:
            assert worlds[p] is None
        else:
            assert worlds[p] == view(game, p), f"player {p}"
    if game is not None:
        for p in game.players:
            worlds.setdefault(p, view(game, p))  # пришёл — получил снимок


def play(seed: int) -> tuple[object, int]:
    rng = Random(seed)
    seats = rng.randint(*parameters.PLAYERS)
    game = None
    worlds: dict = {}
    for step in range(MAX_STEPS):
        if isinstance(game, Finished):
            return game, step
        if rng.random() < GARBAGE:
            actor, cmd = garbage_command(rng)
        elif game is not None and rng.random() < 0.02:
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
        check_worlds(worlds, outcome.game, outcome.events)
        game = outcome.game
        if game is None:  # хост ушёл из лобби — начинаем заново
            seats = rng.randint(*parameters.PLAYERS)
            worlds.clear()
    return game, MAX_STEPS


def test_random_games_finish_keeping_invariants():
    for seed in range(GAMES):
        game, steps = play(seed)
        assert isinstance(game, Finished), f"seed {seed}: no finish in {steps}"


def test_same_seed_same_game():
    assert play(7) == play(7)
