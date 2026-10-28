"""Снимок — то, что игрок знает об игре сейчас.

Скрытое в снимке отсутствует: что в неиспользованных каморах, вес камор
(кроме узнанных предметом), чужие фишки на каморах, чужая выдача до
конца выбора. Лобби и конец игры открыты целиком — их снимок совпадает с
состоянием (`Lobby`, `Finished` из модели данных).

Свой идентификатор клиент знает после Join, поэтому в снимке его нет.
"""

from dataclasses import dataclass, field

from .catalog import Item
from .ids import PlayerID
from .state import Finished, Lobby, Presence, RoundResult, Seat, Settings


@dataclass(frozen=True, slots=True)
class ChamberView:
    """`loaded` известно, только когда камора использована."""

    used: bool = False
    loaded: bool | None = None


@dataclass(frozen=True, slots=True)
class PreparingView:
    size: int
    offer: tuple[Item, ...]
    decided: frozenset[PlayerID] = frozenset()


@dataclass(frozen=True, slots=True)
class ShootingView:
    chambers: tuple[ChamberView, ...]
    chips: tuple[int, ...] | None
    announced: int
    seen: frozendict[int, int] = field(default_factory=frozendict)


type SpreadView = PreparingView | ShootingView


@dataclass(frozen=True, slots=True)
class RoundView:
    start_health: int
    circle: tuple[PlayerID, ...]
    first: PlayerID
    active: PlayerID
    turn: int
    seats: frozendict[PlayerID, Seat]
    spread: SpreadView | None


@dataclass(frozen=True, slots=True)
class GameView:
    settings: Settings
    players: tuple[PlayerID, ...]
    presence: frozendict[PlayerID, Presence]
    results: tuple[RoundResult, ...]
    round: RoundView | None


type View = Lobby | GameView | Finished
