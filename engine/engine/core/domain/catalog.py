"""Справочник предметов (см. docs/engine/architecture/domain/commands.md).

Что предмет делает — в правилах; здесь только неизменные сведения о нём:
класс, какие поля применения он требует и какой эффект оставляет.
Значение `Item` совпадает с именем страницы предмета в docs/rules/items/.
"""

from dataclasses import dataclass
from enum import Enum, auto


class Item(Enum):
    ONE_EYE = "one-eye"
    WIDE_EYES = "wide-eyes"
    REVERSE = "reverse"
    MORE = "more"
    SCARED = "scared"
    PEEK = "peek"
    SHAKE = "shake"
    WATER = "water"
    DUBIOUS = "dubious"
    LIKE_NEW = "like-new"
    PASS = "pass"
    DOUBLE = "double"
    FULL_FORCE = "full-force"
    SHIELD = "shield"
    TRY_THIS = "try-this"
    PLAY_ALONG = "play-along"
    SHARE = "share"
    JACKPOT = "jackpot"


class ItemClass(Enum):
    COMMON = auto()
    RARE = auto()
    CEILING = auto()


class Field(Enum):
    """Поле применения, которое предмет требует указать."""

    PLAYER = auto()
    TARGET = auto()
    CHAMBER = auto()
    TAKE = auto()


@dataclass(frozen=True, slots=True)
class ItemInfo:
    cls: ItemClass
    fields: frozenset[Field] = frozenset()
    leaves_effect: bool = False


def _info(
    cls: ItemClass, *fields: Field, leaves_effect: bool = False
) -> ItemInfo:
    return ItemInfo(cls, frozenset(fields), leaves_effect)


_C, _R, _X = ItemClass.COMMON, ItemClass.RARE, ItemClass.CEILING

CATALOG: dict[Item, ItemInfo] = {
    Item.ONE_EYE: _info(_C, Field.CHAMBER),
    Item.WIDE_EYES: _info(_X),
    Item.REVERSE: _info(_C, Field.CHAMBER),
    Item.MORE: _info(_C),
    Item.SCARED: _info(_C),
    Item.PEEK: _info(_C, Field.CHAMBER),
    Item.SHAKE: _info(_X),
    Item.WATER: _info(_C),
    Item.DUBIOUS: _info(_C),
    Item.LIKE_NEW: _info(_X),
    Item.PASS: _info(_C),
    Item.DOUBLE: _info(_R, leaves_effect=True),
    Item.FULL_FORCE: _info(_R, leaves_effect=True),
    Item.SHIELD: _info(_R, leaves_effect=True),
    Item.TRY_THIS: _info(_R, Field.PLAYER, Field.CHAMBER, leaves_effect=True),
    Item.PLAY_ALONG: _info(_X, Field.PLAYER, Field.TARGET, leaves_effect=True),
    Item.SHARE: _info(_R, Field.PLAYER, Field.TAKE),
    Item.JACKPOT: _info(_X),
}
