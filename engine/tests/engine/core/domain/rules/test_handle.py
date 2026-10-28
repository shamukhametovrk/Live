"""Лобби, связь и вход: всё через `handle`, как будет звать прикладной слой."""

from random import Random

import pytest

from engine.core.domain.commands import (
    ChangeSettings,
    Disconnect,
    Join,
    Leave,
    Prepare,
    Reconnect,
    Shoot,
    Start,
    Timeout,
)
from engine.core.domain.errors import IllegalAction
from engine.core.domain.events import Cancelled, Died, Loaded, Withdrew
from engine.core.domain.ids import PlayerID
from engine.core.domain.rules.handle import handle
from engine.core.domain.state import InProgress, Lobby, Presence, Settings
from tests.engine.core.domain.rules.helpers import A, B, C


def run(game, actor, cmd, seed=0):
    return handle(game, actor, cmd, Random(seed)).game


def lobby_of(*players):
    game = None
    for p in players:
        game = run(game, p, Join())
    return game


def started(*players):
    return run(lobby_of(*players), players[0], Start())


def test_first_to_join_hosts_and_table_holds_six():
    game = lobby_of(*map(PlayerID, range(1, 7)))
    assert game.host == PlayerID(1)
    with pytest.raises(IllegalAction, match="table_full"):
        run(game, PlayerID(7), Join())


def test_host_leaving_cancels_the_game():
    outcome = handle(lobby_of(A, B), A, Leave(), Random(0))
    assert outcome.game is None and outcome.events == [Cancelled()]
    assert run(lobby_of(A, B), B, Leave()).players == (A,)


@pytest.mark.parametrize(
    "settings",
    [
        Settings(rounds=8),
        Settings(health=(1, 5)),
        Settings(chambers=(6, 5)),
        Settings(chambers=(4, 12), cartridges=(4, 4)),
    ],
    ids=["rounds", "health out of bounds", "reversed", "cartridges"],
)
def test_settings_stay_within_parameters(settings):
    with pytest.raises(IllegalAction, match="bad_settings"):
        run(lobby_of(A, B), A, ChangeSettings(settings))


def test_only_host_changes_settings_and_starts():
    for cmd in (ChangeSettings(Settings()), Start()):
        with pytest.raises(IllegalAction, match="not_host"):
            run(lobby_of(A, B), B, cmd)


def test_lobby_pause_blocks_only_start():
    game = run(lobby_of(A, B), None, Disconnect(B))
    game = run(game, C, Join())
    with pytest.raises(IllegalAction, match="paused"):
        run(game, A, Start())
    game = run(game, None, Timeout(B))
    assert isinstance(game, Lobby) and game.players == (A, C)
    assert isinstance(run(game, A, Start()), InProgress)


def test_game_pause_blocks_players_until_return():
    game = run(started(A, B), None, Disconnect(B))
    with pytest.raises(IllegalAction, match="paused"):
        run(game, A, Prepare((), (0,) * game.round.spread.size))
    game = run(game, None, Reconnect(B))
    run(game, A, Prepare((), (0,) * game.round.spread.size))


def test_withdrawal_while_others_wait_loads_the_row():
    game = started(A, B, C)
    size = game.round.spread.size
    game = run(game, A, Prepare((), (0,) * size))
    game = run(game, B, Prepare((), (0,) * size))
    game = run(game, None, Disconnect(C))
    events = handle(game, None, Timeout(C), Random(0)).events
    assert events[0] == Withdrew(C)
    assert Died(C) in events
    assert isinstance(events[-1], Loaded)


def test_withdrawn_player_can_no_longer_act():
    game = started(A, B, C)
    game = run(run(game, None, Disconnect(C)), None, Timeout(C))
    assert game.presence[C] is Presence.WITHDRAWN
    with pytest.raises(IllegalAction, match="not_in_game"):
        run(game, C, Shoot(0, A))


def test_engine_and_players_cannot_swap_commands():
    with pytest.raises(IllegalAction, match="wrong_actor"):
        run(lobby_of(A, B), A, Disconnect(B))
    with pytest.raises(IllegalAction, match="wrong_actor"):
        run(lobby_of(A, B), None, Start())
