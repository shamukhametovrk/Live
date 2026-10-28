"""Команды (см. docs/engine/architecture/domain/commands.md).

Кто действует, в команде нет: его передаёт адаптер.
"""

from dataclasses import dataclass
from enum import Enum, auto

from .catalog import Item
from .ids import PlayerID
from .state import Settings


class Take(Enum):
    """Что «Пора делиться» забирает у соперника."""

    ITEM = auto()
    CHIP = auto()


@dataclass(frozen=True, slots=True)
class Join:
    pass


@dataclass(frozen=True, slots=True)
class Leave:
    pass


@dataclass(frozen=True, slots=True)
class ChangeSettings:
    settings: Settings


@dataclass(frozen=True, slots=True)
class Start:
    pass


@dataclass(frozen=True, slots=True)
class Prepare:
    hand: tuple[Item, ...]
    chips: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class Shoot:
    chamber: int
    target: PlayerID


@dataclass(frozen=True, slots=True)
class UseItem:
    item: Item
    player: PlayerID | None = None
    target: PlayerID | None = None
    chamber: int | None = None
    take: Take | None = None


@dataclass(frozen=True, slots=True)
class Disconnect:
    player: PlayerID


@dataclass(frozen=True, slots=True)
class Reconnect:
    player: PlayerID


@dataclass(frozen=True, slots=True)
class Timeout:
    player: PlayerID


type Command = (
    Join
    | Leave
    | ChangeSettings
    | Start
    | Prepare
    | Shoot
    | UseItem
    | Disconnect
    | Reconnect
    | Timeout
)
