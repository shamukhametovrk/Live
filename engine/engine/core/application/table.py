"""Стол — прикладной слой (см. docs/engine/architecture/application).

Ведёт одну игру: принимает запросы клиентов, зовёт вход домена и через
видимость раздаёт каждому его сообщения. Методы синхронные: адаптер зовёт
их из одного цикла asyncio, поэтому команды идут строго по одной.
"""

import secrets
from dataclasses import dataclass
from random import Random

from ..domain import parameters
from ..domain.commands import (
    Command,
    Disconnect,
    Join,
    Reconnect,
    Timeout,
)
from ..domain.errors import IllegalAction
from ..domain.events import (
    Cancelled,
    Disconnected,
    Event,
    GameStarted,
    Joined,
    Left,
    Reconnected,
    SettingsChanged,
)
from ..domain.ids import PlayerID
from ..domain.rules.handle import handle
from ..domain.state import Finished, Game, InProgress, Lobby, Presence
from ..domain.visibility import project, view
from .ports import (
    ClientID,
    Delivered,
    History,
    Outgoing,
    Rejected,
    Sender,
    Snapshot,
    Timer,
    TokenIssued,
    Welcome,
)

# Запросы клиента, которых нет в домене


@dataclass(frozen=True, slots=True)
class Resume:
    token: str


@dataclass(frozen=True, slots=True)
class AskSnapshot:
    pass


@dataclass(frozen=True, slots=True)
class AskHistory:
    pass


type Request = Command | Resume | AskSnapshot | AskHistory

_LOBBY_EVENTS = (
    Joined,
    Left,
    SettingsChanged,
    Cancelled,
    Disconnected,
    Reconnected,
    GameStarted,
)
_ENGINE_COMMANDS = (Disconnect, Reconnect, Timeout)
_RESET = "reset"  # ключ таймера очистки стола


class Table:
    def __init__(self, sender: Sender, timer: Timer, rng: Random) -> None:
        self._sender = sender
        self._timer = timer
        self._rng = rng
        self._game: Game | None = None
        self._history: list[Event] = []
        self._clients: set[ClientID] = set()
        self._seats: dict[ClientID, PlayerID] = {}
        self._tokens: dict[str, PlayerID] = {}

    # Соединения

    def connect(self, client: ClientID) -> None:
        self._clients.add(client)
        self._sender.send(client, Welcome(client))
        self._send_snapshot(client)

    def disconnect(self, client: ClientID) -> None:
        self._clients.discard(client)
        player = self._seats.pop(client, None)
        game = self._game
        if (
            player is None
            or not isinstance(game, (Lobby, InProgress))
            or game.presence.get(player) is not Presence.PRESENT
        ):
            return
        self._execute(None, Disconnect(player))
        self._timer.start(
            player, parameters.RECONNECT_WAIT, lambda: self._timeout(player)
        )

    # Запросы

    def receive(self, client: ClientID, request: Request) -> None:
        match request:
            case Resume(token):
                self._resume(client, token)
            case AskSnapshot():
                self._send_snapshot(client)
            case AskHistory():
                if isinstance(self._game, Finished):
                    events = tuple(self._history)
                    self._sender.send(client, History(events))
                else:
                    self._reject(client, "game_not_finished")
            case Join():
                actor = self._seats.get(client, PlayerID(client))
                if self._run(client, actor, request):
                    self._seats[client] = actor
                    token = secrets.token_urlsafe(16)
                    self._tokens[token] = actor
                    self._sender.send(client, TokenIssued(token))
                    self._send_snapshot(client)
            case _ if isinstance(request, _ENGINE_COMMANDS):
                self._reject(client, "bad_request")
            case _:
                actor = self._seats.get(client)
                if actor is None:
                    self._reject(client, "not_joined")
                else:
                    self._run(client, actor, request)

    # Внутреннее

    def _resume(self, client: ClientID, token: str) -> None:
        player = self._tokens.get(token)
        if player is None or self._game is None:
            self._reject(client, "bad_token")
            return
        for other, seated in list(self._seats.items()):
            if seated == player:
                del self._seats[other]  # старое соединение могло зависнуть
        self._seats[client] = player
        self._timer.cancel(player)
        game = self._game
        if (
            isinstance(game, (Lobby, InProgress))
            and game.presence.get(player) is Presence.AWAY
        ):
            self._execute(None, Reconnect(player))
        self._send_snapshot(client)

    def _timeout(self, player: PlayerID) -> None:
        game = self._game
        if (
            isinstance(game, (Lobby, InProgress))
            and game.presence.get(player) is Presence.AWAY
        ):
            self._execute(None, Timeout(player))

    def _run(self, client: ClientID, actor: PlayerID, cmd: Command) -> bool:
        try:
            self._execute(actor, cmd)
        except IllegalAction as error:
            self._reject(client, error.code)
            return False
        return True

    def _execute(self, actor: PlayerID | None, cmd: Command) -> None:
        """Выполняет команду и раздаёт сообщения; отказ — IllegalAction."""
        before = self._game
        outcome = handle(before, actor, cmd, self._rng)
        self._game = outcome.game
        self._history += outcome.events
        players = set(_players(before)) | set(_players(outcome.game))
        for client in sorted(self._clients):
            player = self._seats.get(client)
            if player in players:
                for event in outcome.events:
                    self._send(client, Delivered(project(event, player)))
            elif before is None or isinstance(before, Lobby):
                for event in _until_start(outcome.events):
                    self._send(client, Delivered(event))
        if outcome.game is None:  # хост ушёл — игры и токенов больше нет
            self._seats.clear()
            self._tokens.clear()
        elif isinstance(outcome.game, Finished) and not isinstance(
            before, Finished
        ):
            self._timer.start(_RESET, parameters.RESET_WAIT, self._reset)
        else:
            gone = set(_players(before)) - set(_players(outcome.game))
            for client, player in list(self._seats.items()):
                if player in gone:
                    del self._seats[client]

    def _reset(self) -> None:
        """Пустой стол после конца игры: можно садиться заново."""
        self._game = None
        self._history.clear()
        self._seats.clear()
        self._tokens.clear()
        for client in sorted(self._clients):
            self._send_snapshot(client)

    def _send_snapshot(self, client: ClientID) -> None:
        game = self._game
        player = self._seats.get(client)
        if game is None:
            shown = None
        elif player is not None and player in _players(game):
            shown = view(game, player)
        elif isinstance(game, InProgress):
            shown = None  # не севшему идущая игра не видна
        else:
            shown = game
        self._send(client, Snapshot(shown))

    def _reject(self, client: ClientID, code: str) -> None:
        self._send(client, Rejected(code))

    def _send(self, client: ClientID, out: Outgoing) -> None:
        self._sender.send(client, out)


def _players(game: Game | None) -> tuple[PlayerID, ...]:
    return () if game is None else game.players


def _until_start(events: list[Event]) -> list[Event]:
    """События лобби вплоть до начала игры — то, что видит не севший."""
    shown: list[Event] = []
    for event in events:
        if not isinstance(event, _LOBBY_EVENTS):
            break
        shown.append(event)
        if isinstance(event, GameStarted):
            break
    return shown
