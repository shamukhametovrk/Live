"""Сообщения — то, что игрок узнаёт о произошедшем.

Большинство сообщений совпадает с событиями движка: их видят все. У
восьми событий есть скрытое; здесь у них — видимая игроку версия (см.
docs/engine/architecture/domain/commands.md, колонку «Скрыто»).
"""

from dataclasses import dataclass

from .catalog import Item
from .ids import PlayerID
from .state import Effect, Settings

# Лобби и присутствие


@dataclass(frozen=True, slots=True)
class Joined:
    player: PlayerID


@dataclass(frozen=True, slots=True)
class Left:
    player: PlayerID


@dataclass(frozen=True, slots=True)
class SettingsChanged:
    settings: Settings


@dataclass(frozen=True, slots=True)
class Cancelled:
    pass


@dataclass(frozen=True, slots=True)
class Disconnected:
    player: PlayerID


@dataclass(frozen=True, slots=True)
class Reconnected:
    player: PlayerID


@dataclass(frozen=True, slots=True)
class Withdrew:
    player: PlayerID


# Раунд и ряд


@dataclass(frozen=True, slots=True)
class GameStarted:
    players: tuple[PlayerID, ...]


@dataclass(frozen=True, slots=True)
class RoundStarted:
    start_health: int
    circle: tuple[PlayerID, ...]
    first: PlayerID


@dataclass(frozen=True, slots=True)
class SpreadStarted:
    """`offer` — что выпало этому игроку."""

    size: int
    offer: tuple[Item, ...]


@dataclass(frozen=True, slots=True)
class Prepared:
    player: PlayerID


@dataclass(frozen=True, slots=True)
class Loaded:
    """`chips` — свои фишки по каморам, если игрок их клал."""

    offers: frozendict[PlayerID, tuple[Item, ...]]
    hands: frozendict[PlayerID, tuple[Item, ...]]
    chips: tuple[int, ...] | None
    announced: int


@dataclass(frozen=True, slots=True)
class SpreadEnded:
    pass


@dataclass(frozen=True, slots=True)
class RoundEnded:
    winner: PlayerID


@dataclass(frozen=True, slots=True)
class GameFinished:
    winners: tuple[PlayerID, ...]


# Ход


@dataclass(frozen=True, slots=True)
class Shot:
    shooter: PlayerID
    chamber: int
    target: PlayerID
    loaded: bool
    damage: int


@dataclass(frozen=True, slots=True)
class ChipEarned:
    player: PlayerID


@dataclass(frozen=True, slots=True)
class Died:
    player: PlayerID


@dataclass(frozen=True, slots=True)
class TurnPassed:
    active: PlayerID
    turn: int


@dataclass(frozen=True, slots=True)
class EffectAdded:
    owner: PlayerID
    effect: Effect


@dataclass(frozen=True, slots=True)
class EffectRemoved:
    owner: PlayerID
    effect: Effect


# Предметы


@dataclass(frozen=True, slots=True)
class WeightSeen:
    """`weight` видит только применивший."""

    actor: PlayerID
    chamber: int
    weight: int | None


@dataclass(frozen=True, slots=True)
class WeightsSeen:
    """`weights` видит только применивший."""

    actor: PlayerID
    weights: tuple[int, ...] | None


@dataclass(frozen=True, slots=True)
class Reversed:
    actor: PlayerID
    chamber: int


@dataclass(frozen=True, slots=True)
class CartridgeAdded:
    actor: PlayerID


@dataclass(frozen=True, slots=True)
class CartridgeRemoved:
    actor: PlayerID


@dataclass(frozen=True, slots=True)
class Peeked:
    actor: PlayerID
    chamber: int
    loaded: bool


@dataclass(frozen=True, slots=True)
class Shaken:
    actor: PlayerID


@dataclass(frozen=True, slots=True)
class Healed:
    actor: PlayerID
    item: Item
    amount: int


@dataclass(frozen=True, slots=True)
class Gambled:
    actor: PlayerID
    won: bool
    amount: int


@dataclass(frozen=True, slots=True)
class Passed:
    actor: PlayerID


@dataclass(frozen=True, slots=True)
class ItemStolen:
    actor: PlayerID
    victim: PlayerID
    item: Item


@dataclass(frozen=True, slots=True)
class ChipStolen:
    actor: PlayerID
    victim: PlayerID


@dataclass(frozen=True, slots=True)
class Jackpot:
    actor: PlayerID


@dataclass(frozen=True, slots=True)
class Wasted:
    actor: PlayerID
    item: Item


type Message = (
    Joined
    | Left
    | SettingsChanged
    | Cancelled
    | Disconnected
    | Reconnected
    | Withdrew
    | GameStarted
    | RoundStarted
    | SpreadStarted
    | Prepared
    | Loaded
    | SpreadEnded
    | RoundEnded
    | GameFinished
    | Shot
    | ChipEarned
    | Died
    | TurnPassed
    | EffectAdded
    | EffectRemoved
    | WeightSeen
    | WeightsSeen
    | Reversed
    | CartridgeAdded
    | CartridgeRemoved
    | Peeked
    | Shaken
    | Healed
    | Gambled
    | Passed
    | ItemStolen
    | ChipStolen
    | Jackpot
    | Wasted
)
