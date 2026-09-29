from engine.core.domain.enums import GameStage, Presence
from engine.core.domain.exceptions.game import (
    GameLobbyError,
    GameStageError,
)
from engine.core.domain.ids import PlayerID
from engine.core.domain.value_objects import GameSettings, GameState

from .match import Match

MIN_PLAYERS = 2
MAX_PLAYERS = 6


class Game:
    """Игра — корень агрегата: всё от лобби до конца игры.

    Хранит стадию, настройки, хоста, игроков, их присутствие, счётчики
    начатых партий, число сыгранных партий и текущую партию. Правил игры
    не содержит: кто хост и может ли он отдать команду, кто начинает
    партию и когда её начинать — решает правило.

    Счётчики начатых и сыгранных партий игра ведёт сама: так они не
    могут разойтись с партиями.

    Ошибки:
    - наследники `GameError` — недопустимое действие игрока;
    - `ValueError` — баг правила или адаптера.
    """

    __slots__ = (
        "_first_moves",
        "_host",
        "_match",
        "_matches_played",
        "_players",
        "_presence",
        "_settings",
        "_stage",
    )

    def __init__(self) -> None:
        """Создаёт пустое лобби с настройками по умолчанию."""
        self._stage = GameStage.LOBBY
        self._settings = GameSettings()
        self._host: PlayerID | None = None
        self._players: list[PlayerID] = []
        self._presence: dict[PlayerID, Presence] = {}
        self._first_moves: dict[PlayerID, int] = {}
        self._matches_played = 0
        self._match: Match | None = None

    # Проверки

    def __check_player(self, player: PlayerID) -> None:
        """Бросает ValueError, если игрока в игре нет."""
        if player not in self._players:
            raise ValueError(f"player {player} is not in game")

    def __check_match_over(self) -> Match:
        """Возвращает текущую партию, если она окончена
        (жив не больше одного)."""
        match = self.match
        if len(match.alive) > 1:
            raise ValueError(
                f"current match is not over: alive {list(match.alive)}"
            )
        return match

    # Лобби

    @property
    def stage(self) -> GameStage:
        """Стадия игры."""
        return self._stage

    @property
    def host(self) -> PlayerID | None:
        """Хост — первый присоединившийся; None, пока никого нет."""
        return self._host

    @property
    def players(self) -> tuple[PlayerID, ...]:
        """Игроки в порядке Join."""
        return tuple(self._players)

    @property
    def settings(self) -> GameSettings:
        """Настройки хоста. Менять можно только в лобби."""
        return self._settings

    @settings.setter
    def settings(self, value: GameSettings) -> None:
        if self._stage is not GameStage.LOBBY:
            raise GameStageError("settings can be changed only in lobby")
        # - - -
        self._settings = value

    def join(self, player: PlayerID) -> None:
        """Присоединяет игрока. Первый присоединившийся становится хостом."""
        if self._stage is not GameStage.LOBBY:
            raise GameStageError("players can join only in lobby")
        if player in self._players:
            raise GameLobbyError(f"player {player} has already joined")
        if len(self._players) >= MAX_PLAYERS:
            raise GameLobbyError(f"game is full: {MAX_PLAYERS} players")
        # - - -
        self._players.append(player)
        if self._host is None:
            self._host = player

    def leave(self, player: PlayerID) -> None:
        """Убирает игрока из лобби. Хост уйти не может: это конец игры."""
        if self._stage is not GameStage.LOBBY:
            raise ValueError("players can leave only in lobby")
        self.__check_player(player)
        if player == self._host:
            raise ValueError("host leaving the lobby ends the game")
        # - - -
        self._players.remove(player)

    # Присутствие

    def presence(self, player: PlayerID) -> Presence:
        """Присутствие игрока. ValueError в лобби или для чужого игрока."""
        if self._stage is GameStage.LOBBY:
            raise ValueError("presence exists only after start")
        self.__check_player(player)
        return self._presence[player]

    def __move_presence(
        self, player: PlayerID, source: Presence, target: Presence
    ) -> None:
        """Переводит присутствие из `source` в `target`, иначе ValueError."""
        current = self.presence(player)
        if current is not source:
            raise ValueError(
                f"player {player} must be {source.name} to become "
                f"{target.name}, got {current.name}"
            )
        # - - -
        self._presence[player] = target

    def disconnect(self, player: PlayerID) -> None:
        """На связи → нет связи."""
        self.__move_presence(player, Presence.PRESENT, Presence.AWAY)

    def reconnect(self, player: PlayerID) -> None:
        """Нет связи → на связи."""
        self.__move_presence(player, Presence.AWAY, Presence.PRESENT)

    def withdraw(self, player: PlayerID) -> None:
        """Нет связи → выбыл насовсем. Обратно нельзя."""
        self.__move_presence(player, Presence.AWAY, Presence.WITHDRAWN)

    @property
    def remaining(self) -> tuple[PlayerID, ...]:
        """Невыбывшие игроки в порядке Join."""
        return tuple(
            p
            for p in self._players
            if self._presence.get(p) is not Presence.WITHDRAWN
        )

    @property
    def anyone_away(self) -> bool:
        """Есть ли кто-то без связи — для правила «игра ждёт»."""
        return Presence.AWAY in self._presence.values()

    # Партии

    @property
    def matches_played(self) -> int:
        """Сколько партий сыграно."""
        return self._matches_played

    def first_moves(self, player: PlayerID) -> int:
        """Сколько партий игрок начинал; 0 в лобби."""
        self.__check_player(player)
        return self._first_moves.get(player, 0)

    @property
    def match(self) -> Match:
        """Текущая партия. ValueError вне стадии «идёт партия»."""
        if self._match is None:
            raise ValueError(f"no match in stage {self._stage.name}")
        return self._match

    def start_match(self, match: Match) -> None:
        """Начинает партию: первую — из лобби, следующую — после текущей.

        Начавший партию (её активный игрок) получает +1 к начатым партиям.
        Следующая партия засчитывает текущую сыгранной.
        """
        players = set(match.turn_circle)
        if self._stage is GameStage.LOBBY:
            if not (MIN_PLAYERS <= len(self._players) <= MAX_PLAYERS):
                raise ValueError(
                    f"game needs {MIN_PLAYERS}..{MAX_PLAYERS} players, "
                    f"got {len(self._players)}"
                )
            if players != set(self._players):
                raise ValueError("first match must include all players")
        elif self._stage is GameStage.IN_MATCH:
            self.__check_match_over()
            if self._matches_played + 1 >= self._settings.matches:
                raise ValueError("all matches are played, finish instead")
            if len(self.remaining) < MIN_PLAYERS:
                raise ValueError("too few players remain, finish instead")
            if players != set(self.remaining):
                raise ValueError("next match must include remaining players")
        else:
            raise ValueError("game is finished")
        # - - -

        if self._stage is GameStage.LOBBY:
            self._stage = GameStage.IN_MATCH
            self._presence = dict.fromkeys(self._players, Presence.PRESENT)
            self._first_moves = dict.fromkeys(self._players, 0)
        else:
            self._matches_played += 1
        self._first_moves[match.active] += 1
        self._match = match

    def finish(self) -> None:
        """Заканчивает игру после текущей партии; она засчитывается сыгранной.

        Только если сыграны все партии или невыбывших меньше двух.
        """
        if self._stage is not GameStage.IN_MATCH:
            raise ValueError("game can finish only during a match")
        self.__check_match_over()
        all_played = self._matches_played + 1 >= self._settings.matches
        if not (all_played or len(self.remaining) < MIN_PLAYERS):
            raise ValueError("matches remain and enough players are left")
        # - - -
        self._matches_played += 1
        self._match = None
        self._stage = GameStage.FINISHED

    # Снимок

    @property
    def state(self) -> GameState:
        """Полный снимок игры, включая служебное и скрытое."""
        return GameState(
            stage=self._stage,
            settings=self._settings,
            host=self._host,
            players=tuple(self._players),
            presence=frozendict(self._presence),  # type: ignore
            first_moves=frozendict(self._first_moves),  # type: ignore
            matches_played=self._matches_played,
            match=None if self._match is None else self._match.state,
        )
