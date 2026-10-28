"""Лобби (см. правила домена, «Лобби»)."""

from dataclasses import replace
from random import Random

from .. import parameters
from ..commands import ChangeSettings
from ..errors import IllegalAction
from ..events import (
    Cancelled,
    Event,
    GameStarted,
    Joined,
    Left,
    SettingsChanged,
)
from ..ids import PlayerID
from ..state import InProgress, Lobby, Presence, Settings
from .round import start_round


def join(game: Lobby | None, actor: PlayerID) -> tuple[Lobby, list[Event]]:
    if game is None:
        lobby = Lobby(actor, (actor,), frozendict({actor: Presence.PRESENT}))
        return lobby, [Joined(actor)]
    if actor in game.players:
        raise IllegalAction("already_joined")
    if len(game.players) >= parameters.PLAYERS[1]:
        raise IllegalAction("table_full")
    # - - -
    lobby = replace(
        game,
        players=(*game.players, actor),
        presence=game.presence | {actor: Presence.PRESENT},
    )
    return lobby, [Joined(actor)]


def leave(game: Lobby, player: PlayerID) -> tuple[Lobby | None, list[Event]]:
    """Уход из-за стола; ушёл хост — игры нет."""
    if player not in game.players:
        raise IllegalAction("not_at_table")
    # - - -
    if player == game.host:
        return None, [Cancelled()]
    lobby = replace(
        game,
        players=tuple(p for p in game.players if p != player),
        presence=frozendict(
            {p: s for p, s in game.presence.items() if p != player}
        ),
    )
    return lobby, [Left(player)]


def change_settings(
    game: Lobby, actor: PlayerID, cmd: ChangeSettings
) -> tuple[Lobby, list[Event]]:
    if actor != game.host:
        raise IllegalAction("not_host")
    if not valid(cmd.settings):
        raise IllegalAction("bad_settings")
    # - - -
    return replace(game, settings=cmd.settings), [SettingsChanged(cmd.settings)]


def start(
    game: Lobby, actor: PlayerID, rng: Random
) -> tuple[InProgress, list[Event]]:
    if actor != game.host:
        raise IllegalAction("not_host")
    low, high = parameters.PLAYERS
    if not low <= len(game.players) <= high:
        raise IllegalAction("wrong_number_of_players")
    if Presence.AWAY in game.presence.values():
        raise IllegalAction("paused")
    # - - -
    round_, events = start_round(game.settings, game.players, (), rng)
    started = InProgress(game.settings, game.players, game.presence, (), round_)
    return started, [GameStarted(game.players), *events]


def valid(settings: Settings) -> bool:
    """Настройки в пределах параметров (см. docs/rules/parameters.md)."""

    def within(value: tuple[int, int], bounds: tuple[int, int]) -> bool:
        return bounds[0] <= value[0] <= value[1] <= bounds[1]

    low, high = parameters.ROUNDS
    return (
        low <= settings.rounds <= high
        and within(settings.health, parameters.HEALTH)
        and within(settings.chambers, parameters.CHAMBERS)
        and within(settings.cartridges, parameters.CARTRIDGES)
        and settings.cartridges[0] < settings.chambers[0]
    )
