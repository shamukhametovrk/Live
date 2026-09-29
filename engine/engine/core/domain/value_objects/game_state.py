from dataclasses import dataclass

from engine.core.domain.enums import GameStage, Presence
from engine.core.domain.ids import PlayerID

from .game_settings import GameSettings
from .match_state import MatchState


@dataclass(frozen=True)
class GameState:
    """Неизменяемый снимок игры `Game`, отдаваемый `Game.state`.

    Полный: содержит служебные данные (`first_moves`) и скрытое внутри
    партии. Что из этого видит конкретный игрок, решают правила (см.
    docs/rules/visibility.md).

    - `stage`           — стадия игры.
    - `settings`        — настройки хоста.
    - `host`            — хост; None, пока никто не присоединился.
    - `players`         — игроки в порядке Join.
    - `presence`        — присутствие каждого игрока; пусто в лобби.
    - `first_moves`     — сколько партий начал каждый; служебные данные.
    - `matches_played`  — сколько партий сыграно.
    - `match`           — снимок текущей партии; None вне партии.
    """

    stage: GameStage
    settings: GameSettings
    host: PlayerID | None
    players: tuple[PlayerID, ...]
    presence: frozendict[PlayerID, Presence]
    first_moves: frozendict[PlayerID, int]
    matches_played: int
    match: MatchState | None
