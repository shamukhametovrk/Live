from enum import Enum


class GameStage(Enum):
    """Стадия игры

    `LOBBY`     — лобби: игроки присоединяются, хост задаёт настройки; \\
    `IN_MATCH`  — идёт партия; \\
    `FINISHED`  — игра окончена, движок ждёт, пока хост его закроет;
    """

    LOBBY = 0
    IN_MATCH = 1
    FINISHED = 2
