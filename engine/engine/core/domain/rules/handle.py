"""Вход в домен (см. правила домена, «Вход»).

Принимает любую команду, проверяет общее — стадию, паузу, кто действует —
и отдаёт её правилу этой стадии.
"""

from dataclasses import dataclass, replace
from random import Random

from ..commands import (
    ChangeSettings,
    Command,
    Disconnect,
    Join,
    Leave,
    Prepare,
    Reconnect,
    Shoot,
    Start,
    Timeout,
    UseItem,
)
from ..errors import IllegalAction
from ..events import Event
from ..ids import PlayerID
from ..state import Finished, Game, InProgress, Lobby, Presence
from . import lobby, presence
from .apply import apply
from .prepare import prepare
from .settle import settle
from .shoot import shoot

_ENGINE_COMMANDS = (Disconnect, Reconnect, Timeout)


@dataclass(frozen=True, slots=True)
class Outcome:
    game: Game | None
    events: list[Event]


def handle(
    game: Game | None, actor: PlayerID | None, cmd: Command, rng: Random
) -> Outcome:
    """Новое состояние и события; недопустимая команда — IllegalAction.

    `actor` — кто действует; None — сам движок (связь, таймаут).
    """
    if (actor is None) != isinstance(cmd, _ENGINE_COMMANDS):
        raise IllegalAction("wrong_actor")
    if isinstance(game, Finished):
        raise IllegalAction("game_finished")
    match cmd:
        case Disconnect(player) | Reconnect(player) | Timeout(player):
            if game is None:
                raise IllegalAction("no_game")
            return _presence(game, cmd, player, rng)
    assert actor is not None
    if game is None or isinstance(game, Lobby):
        return _lobby(game, actor, cmd, rng)
    return _in_progress(game, actor, cmd, rng)


def _presence(
    game: Lobby | InProgress, cmd: Command, player: PlayerID, rng: Random
) -> Outcome:
    match cmd:
        case Disconnect():
            return Outcome(*presence.disconnect(game, player))
        case Reconnect():
            return Outcome(*presence.reconnect(game, player))
        case _:
            return Outcome(*presence.timeout(game, player, rng))


def _lobby(
    game: Lobby | None, actor: PlayerID, cmd: Command, rng: Random
) -> Outcome:
    if isinstance(cmd, Join):
        return Outcome(*lobby.join(game, actor))
    if game is None:
        raise IllegalAction("no_game")
    match cmd:
        case Leave():
            return Outcome(*lobby.leave(game, actor))
        case ChangeSettings():
            return Outcome(*lobby.change_settings(game, actor, cmd))
        case Start():
            return Outcome(*lobby.start(game, actor, rng))
        case _:
            raise IllegalAction("not_started")


def _in_progress(
    game: InProgress, actor: PlayerID, cmd: Command, rng: Random
) -> Outcome:
    if not isinstance(cmd, (Prepare, Shoot, UseItem)):
        raise IllegalAction("game_started")
    if game.presence.get(actor) in (None, Presence.WITHDRAWN):
        raise IllegalAction("not_in_game")
    if Presence.AWAY in game.presence.values():
        raise IllegalAction("paused")
    round_ = game.round
    match cmd:
        case Prepare():
            new_round, events = prepare(game.settings, round_, actor, cmd, rng)
            return Outcome(replace(game, round=new_round), events)
        case Shoot():
            new_round, events, ends_turn = shoot(round_, actor, cmd)
        case UseItem():
            new_round, events, ends_turn = apply(round_, actor, cmd, rng)
    settled, more = settle(game, new_round, round_.alive, ends_turn, rng)
    return Outcome(settled, events + more)
