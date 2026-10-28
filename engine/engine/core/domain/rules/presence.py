"""Связь: потеря, возврат и таймаут (см. правила домена)."""

from dataclasses import replace
from random import Random

from ..errors import IllegalAction
from ..events import Disconnected, Event, Reconnected, Withdrew
from ..ids import PlayerID
from ..state import Game, InProgress, Lobby, Preparing, Presence
from .lobby import leave
from .prepare import load_if_ready
from .settle import settle


def disconnect(
    game: Lobby | InProgress, player: PlayerID
) -> tuple[Lobby | InProgress, list[Event]]:
    _expect(game, player, Presence.PRESENT)
    presence = game.presence | {player: Presence.AWAY}
    return replace(game, presence=presence), [Disconnected(player)]


def reconnect(
    game: Lobby | InProgress, player: PlayerID
) -> tuple[Lobby | InProgress, list[Event]]:
    _expect(game, player, Presence.AWAY)
    presence = game.presence | {player: Presence.PRESENT}
    return replace(game, presence=presence), [Reconnected(player)]


def timeout(
    game: Lobby | InProgress, player: PlayerID, rng: Random
) -> tuple[Game | None, list[Event]]:
    """Не вернулся вовремя: в лобби уходит, в игре выбывает."""
    _expect(game, player, Presence.AWAY)
    if isinstance(game, Lobby):
        return leave(game, player)
    # - - -
    game = replace(game, presence=game.presence | {player: Presence.WITHDRAWN})
    events: list[Event] = [Withdrew(player)]
    round_ = game.round
    alive_before = round_.alive
    if round_.seats[player].alive:
        seats = round_.seats | {player: replace(round_.seats[player], health=0)}
        round_ = replace(round_, seats=seats)
    settled, more = settle(game, round_, alive_before, False, rng)
    events += more
    if isinstance(settled, InProgress) and isinstance(
        settled.round.spread, Preparing
    ):
        round_, loaded = load_if_ready(settled.settings, settled.round, rng)
        settled = replace(settled, round=round_)
        events += loaded
    return settled, events


def _expect(
    game: Lobby | InProgress, player: PlayerID, presence: Presence
) -> None:
    if game.presence.get(player) is not presence:
        raise IllegalAction("wrong_presence")
