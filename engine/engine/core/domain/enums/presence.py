from enum import Enum


class Presence(Enum):
    """Присутствие игрока после старта игры

    `PRESENT`    — на связи; \\
    `AWAY`       — нет связи, игра ждёт; \\
    `WITHDRAWN`  — выбыл насовсем;
    """

    PRESENT = 0
    AWAY = 1
    WITHDRAWN = 2
