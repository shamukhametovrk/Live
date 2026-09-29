from collections.abc import Mapping, Sequence

from engine.core.domain.ids import PlayerID
from engine.core.domain.value_objects import MatchState

from .preparation import Preparation
from .round import Round
from .seat import Seat


class Match:
    """Партия — места игроков, очередь хода и текущая стадия.

    Составная сущность: хранит места (`Seat`) и либо подготовку
    (`Preparation`), либо раунд (`Round`). Охраняет то, как части
    сложены вместе; то, что внутри частей, охраняют они сами.

    Ход передаётся всегда следующему живому по кругу — это свойство
    очереди, поэтому его держит партия. Когда передавать ход и когда
    менять стадию — решает правило.

    Ошибки — `ValueError`: всё, что меняет партию, вычисляет правило.
    """

    __slots__ = (
        "_active",
        "_seats",
        "_stage",
        "_turn_circle",
        "_turn_number",
    )

    def __init__(
        self,
        seats: Mapping[PlayerID, Seat],
        turn_circle: Sequence[PlayerID],
        first_player: PlayerID,
        preparation: Preparation,
    ) -> None:
        """Создаёт партию: первый ход у `first_player`, стадия — подготовка.

        seats         — места всех игроков партии.
        turn_circle   — очередь хода по кругу, уже перетасованная.
        first_player  — кто начинает партию.
        preparation   — подготовка к первому раунду.
        """
        self.__check_circle(seats, turn_circle)
        if first_player not in seats:
            raise ValueError(f"first player {first_player} is not in match")
        # - - -

        self._seats: dict[PlayerID, Seat] = dict(seats)
        self._turn_circle: tuple[PlayerID, ...] = tuple(turn_circle)
        self._active = first_player
        self._turn_number = 1

        self.__check_participants(preparation)
        self._stage: Preparation | Round = preparation

    # Проверки

    @staticmethod
    def __check_circle(
        seats: Mapping[PlayerID, Seat], turn_circle: Sequence[PlayerID]
    ) -> None:
        """Проверяет, что очередь — это ровно игроки с местами, без повторов."""
        if len(turn_circle) < 2:
            raise ValueError(
                f"match needs at least 2 players, got {len(turn_circle)}"
            )
        if len(set(turn_circle)) != len(turn_circle):
            raise ValueError(f"turn circle has duplicates: {turn_circle}")
        if set(turn_circle) != set(seats):
            raise ValueError(
                f"turn circle {sorted(turn_circle)} must match seats "
                f"{sorted(seats)}"
            )

    def __check_participants(self, preparation: Preparation) -> None:
        """Проверяет, что участники подготовки — ровно живые игроки."""
        alive = frozenset(self.alive)
        if preparation.participants != alive:
            raise ValueError(
                f"preparation participants {sorted(preparation.participants)} "
                f"must be the alive players {sorted(alive)}"
            )

    # Места и очередь

    def seat(self, player: PlayerID) -> Seat:
        """Место игрока. ValueError, если игрока в партии нет."""
        if player not in self._seats:
            raise ValueError(f"player {player} is not in match")
        return self._seats[player]

    @property
    def turn_circle(self) -> tuple[PlayerID, ...]:
        """Очередь хода по кругу."""
        return self._turn_circle

    @property
    def alive(self) -> tuple[PlayerID, ...]:
        """Живые игроки в порядке очереди."""
        return tuple(p for p in self._turn_circle if self._seats[p].is_alive)

    # Ход

    @property
    def active(self) -> PlayerID:
        """Чей сейчас ход."""
        return self._active

    @property
    def turn_number(self) -> int:
        """Номер хода в партии; не сбрасывается между раундами."""
        return self._turn_number

    def pass_turn(self) -> None:
        """Передаёт ход следующему живому по кругу; номер хода растёт.

        Мёртвые пропускаются. Если живой один — ход переходит к нему, даже
        если он и был активным. ValueError, если живых нет вовсе.
        """
        start = self._turn_circle.index(self._active)
        size = len(self._turn_circle)
        for step in range(1, size + 1):
            candidate = self._turn_circle[(start + step) % size]
            if self._seats[candidate].is_alive:
                break
        else:
            raise ValueError("no alive players to pass the turn to")
        # - - -
        self._active = candidate
        self._turn_number += 1

    # Стадия

    @property
    def in_round(self) -> bool:
        """Идёт ли раунд (иначе — подготовка)."""
        return isinstance(self._stage, Round)

    @property
    def preparation(self) -> Preparation:
        """Текущая подготовка. ValueError, если идёт раунд."""
        if not isinstance(self._stage, Preparation):
            raise ValueError("match is in round, not in preparation")
        return self._stage

    @property
    def round(self) -> Round:
        """Текущий раунд. ValueError, если идёт подготовка."""
        if not isinstance(self._stage, Round):
            raise ValueError("match is in preparation, not in round")
        return self._stage

    def start_round(self, round_: Round) -> None:
        """Подготовка закончилась — начинается раунд."""
        if not isinstance(self._stage, Preparation):
            raise ValueError("round can start only after preparation")
        # - - -
        self._stage = round_

    def start_preparation(self, preparation: Preparation) -> None:
        """Раунд закончился — начинается подготовка к следующему.

        Участники подготовки — ровно живые игроки.
        """
        if not isinstance(self._stage, Round):
            raise ValueError("preparation can start only after a round")
        self.__check_participants(preparation)
        # - - -
        self._stage = preparation

    # Снимок

    @property
    def state(self) -> MatchState:
        """Полный снимок партии, включая скрытое."""
        return MatchState(
            turn_circle=self._turn_circle,
            active=self._active,
            turn_number=self._turn_number,
            seats=frozendict(
                {player: seat.state for player, seat in self._seats.items()}  # type: ignore
            ),
            stage=self._stage.state,
        )
