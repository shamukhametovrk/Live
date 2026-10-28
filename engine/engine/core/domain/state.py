"""Модель данных (см. docs/engine/architecture/domain/state.md).

Всё состояние игры неизменяемо. Правила не меняют его, а возвращают
новое. Здесь нет проверок: допустимость команды проверяет правило, а
инварианты состояния — тесты.
"""

from dataclasses import dataclass, field
from enum import Enum, auto

from . import parameters
from .catalog import Item
from .ids import PlayerID

# Игра


class Presence(Enum):
    PRESENT = auto()
    AWAY = auto()
    WITHDRAWN = auto()


@dataclass(frozen=True, slots=True)
class Settings:
    """Настройки хоста. По умолчанию пределы из параметров целиком."""

    rounds: int = parameters.DEFAULT_ROUNDS
    health: tuple[int, int] = parameters.HEALTH
    chambers: tuple[int, int] = parameters.CHAMBERS
    cartridges: tuple[int, int] = parameters.CARTRIDGES
    excluded: frozenset[Item] = frozenset()


@dataclass(frozen=True, slots=True)
class RoundResult:
    first: PlayerID
    winner: PlayerID


@dataclass(frozen=True, slots=True)
class Lobby:
    host: PlayerID
    players: tuple[PlayerID, ...]
    presence: frozendict[PlayerID, Presence]
    settings: Settings = Settings()


@dataclass(frozen=True, slots=True)
class InProgress:
    settings: Settings
    players: tuple[PlayerID, ...]
    presence: frozendict[PlayerID, Presence]
    results: tuple[RoundResult, ...]
    round: Round


@dataclass(frozen=True, slots=True)
class Finished:
    players: tuple[PlayerID, ...]
    presence: frozendict[PlayerID, Presence]
    results: tuple[RoundResult, ...]


type Game = Lobby | InProgress | Finished


# Эффекты: данные без поведения (см. решение 0015).
# turn — номер хода, в который эффект появился.


@dataclass(frozen=True, slots=True)
class Double:
    turn: int


@dataclass(frozen=True, slots=True)
class FullForce:
    turn: int


@dataclass(frozen=True, slots=True)
class Shield:
    turn: int


@dataclass(frozen=True, slots=True)
class PlayAlong:
    turn: int
    target: PlayerID


@dataclass(frozen=True, slots=True)
class TryThis:
    turn: int
    chamber: int


type Effect = Double | FullForce | Shield | PlayAlong | TryThis


# Раунд


@dataclass(frozen=True, slots=True)
class Seat:
    health: int
    hand: tuple[Item, ...] = ()
    chips: int = 0
    effects: tuple[Effect, ...] = ()

    @property
    def alive(self) -> bool:
        return self.health > 0


@dataclass(frozen=True, slots=True)
class Chamber:
    loaded: bool
    used: bool = False


@dataclass(frozen=True, slots=True)
class Choice:
    hand: tuple[Item, ...]
    chips: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class Preparing:
    size: int
    offers: frozendict[PlayerID, tuple[Item, ...]]
    choices: frozendict[PlayerID, Choice] = field(default_factory=frozendict)


@dataclass(frozen=True, slots=True)
class Shooting:
    chambers: tuple[Chamber, ...]
    chips: frozendict[PlayerID, tuple[int, ...]]
    announced: int
    revealed: frozendict[PlayerID, frozenset[int]] = field(
        default_factory=frozendict
    )

    @property
    def weights(self) -> tuple[int, ...]:
        """Вес каморы — единица плюс все фишки на ней, не важно чьи."""
        return tuple(
            1 + sum(chips[i] for chips in self.chips.values())
            for i in range(len(self.chambers))
        )


type Spread = Preparing | Shooting


@dataclass(frozen=True, slots=True)
class Round:
    start_health: int
    circle: tuple[PlayerID, ...]
    first: PlayerID
    active: PlayerID
    turn: int
    seats: frozendict[PlayerID, Seat]
    spread: Spread

    @property
    def alive(self) -> tuple[PlayerID, ...]:
        """Живые игроки в порядке круга."""
        return tuple(p for p in self.circle if self.seats[p].alive)
