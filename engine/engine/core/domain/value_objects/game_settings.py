from dataclasses import dataclass

from engine.core.domain.enums import Item
from engine.core.domain.exceptions.game import GameSettingsError


@dataclass(frozen=True)
class GameSettings:
    """Настройки хоста (см. docs/rules/game.md).

    Значения по умолчанию позволяют запустить игру, ничего не меняя.
    Настройки присылает хост, поэтому нарушение — GameSettingsError.

    - `matches`        — сколько партий в игре.
    - `allowed_items`  — какие предметы участвуют (выстрел — всегда).
    - `max_items`      — лимит предметов на руках.
    - `min_health`     — минимум жизней в начале партии.
    - `max_health`     — максимум жизней в начале партии.
    """

    matches: int = 3
    allowed_items: frozenset[Item] = frozenset(Item)
    max_items: int = 8
    min_health: int = 1
    max_health: int = 5

    def __post_init__(self) -> None:
        if self.matches < 1:
            raise GameSettingsError(f"matches must be >= 1, got {self.matches}")
        if self.max_items < 0:
            raise GameSettingsError(
                f"max_items must be >= 0, got {self.max_items}"
            )
        if not (1 <= self.min_health <= self.max_health):
            raise GameSettingsError(
                f"health must satisfy 1 <= min <= max, "
                f"got min {self.min_health}, max {self.max_health}"
            )
