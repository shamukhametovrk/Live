"""Числа игры (см. docs/rules/parameters.md).

Пределы «от–до» — включительно. Те, что помечены в правилах как
настройка, хост может сузить, но не расширить.
"""

from .catalog import ItemClass

PLAYERS = (2, 6)
ROUNDS = (1, 7)
HEALTH = (2, 5)
CHAMBERS = (4, 12)
CARTRIDGES = (1, 11)
HAND_LIMIT = 8

DEAL_SIZE = (0, 4)
DEAL_CLASS_ODDS = {
    ItemClass.COMMON: 60,
    ItemClass.RARE: 30,
    ItemClass.CEILING: 10,
}

DEFAULT_ROUNDS = 3

RECONNECT_WAIT = 60  # секунд
RESET_WAIT = 10  # секунд от конца игры до пустого стола
