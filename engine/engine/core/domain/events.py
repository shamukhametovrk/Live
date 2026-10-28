"""События (см. docs/engine/architecture/domain/commands.md).

Событие — полная правда, включая скрытое. Открытые всем события — те же
классы, что сообщения (messages.py). Здесь заново объявлены только восемь
событий со скрытыми полями; их видимые версии — среди сообщений.
"""

from dataclasses import dataclass

from .catalog import Item
from .ids import PlayerID
from .messages import (
    Cancelled,
    ChipEarned,
    ChipStolen,
    Died,
    Disconnected,
    EffectAdded,
    EffectRemoved,
    Gambled,
    GameFinished,
    GameStarted,
    Healed,
    ItemStolen,
    Jackpot,
    Joined,
    Left,
    Passed,
    Peeked,
    Prepared,
    Reconnected,
    RoundEnded,
    RoundStarted,
    SettingsChanged,
    Shot,
    SpreadEnded,
    TurnPassed,
    Wasted,
    Withdrew,
)

type Public = (
    Joined
    | Left
    | SettingsChanged
    | Cancelled
    | Disconnected
    | Reconnected
    | Withdrew
    | GameStarted
    | RoundStarted
    | Prepared
    | SpreadEnded
    | RoundEnded
    | GameFinished
    | Shot
    | ChipEarned
    | Died
    | TurnPassed
    | EffectAdded
    | EffectRemoved
    | Peeked
    | Healed
    | Gambled
    | Passed
    | ItemStolen
    | ChipStolen
    | Jackpot
    | Wasted
)


@dataclass(frozen=True, slots=True)
class SpreadStarted:
    size: int
    offers: frozendict[PlayerID, tuple[Item, ...]]


@dataclass(frozen=True, slots=True)
class Loaded:
    offers: frozendict[PlayerID, tuple[Item, ...]]
    hands: frozendict[PlayerID, tuple[Item, ...]]
    chips: frozendict[PlayerID, tuple[int, ...]]
    loaded: tuple[bool, ...]
    announced: int


@dataclass(frozen=True, slots=True)
class WeightSeen:
    actor: PlayerID
    chamber: int
    weight: int


@dataclass(frozen=True, slots=True)
class WeightsSeen:
    actor: PlayerID
    weights: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class Reversed:
    actor: PlayerID
    chamber: int
    now_loaded: bool


@dataclass(frozen=True, slots=True)
class CartridgeAdded:
    actor: PlayerID
    chamber: int


@dataclass(frozen=True, slots=True)
class CartridgeRemoved:
    actor: PlayerID
    chamber: int


@dataclass(frozen=True, slots=True)
class Shaken:
    actor: PlayerID
    loaded: tuple[bool, ...]


type Hidden = (
    SpreadStarted
    | Loaded
    | WeightSeen
    | WeightsSeen
    | Reversed
    | CartridgeAdded
    | CartridgeRemoved
    | Shaken
)

type Event = Public | Hidden

__all__ = [
    "CartridgeAdded",
    "CartridgeRemoved",
    "Cancelled",
    "ChipEarned",
    "ChipStolen",
    "Died",
    "Disconnected",
    "EffectAdded",
    "EffectRemoved",
    "Event",
    "GameFinished",
    "GameStarted",
    "Gambled",
    "Healed",
    "Hidden",
    "ItemStolen",
    "Jackpot",
    "Joined",
    "Left",
    "Loaded",
    "Passed",
    "Peeked",
    "Prepared",
    "Public",
    "Reconnected",
    "Reversed",
    "RoundEnded",
    "RoundStarted",
    "SettingsChanged",
    "Shaken",
    "Shot",
    "SpreadEnded",
    "SpreadStarted",
    "TurnPassed",
    "Wasted",
    "WeightSeen",
    "WeightsSeen",
    "Withdrew",
]
