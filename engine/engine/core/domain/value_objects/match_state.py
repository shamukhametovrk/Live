from dataclasses import dataclass

from engine.core.domain.ids import PlayerID

from .preparation_state import PreparationState
from .round_state import RoundState
from .seat_state import SeatState


@dataclass(frozen=True)
class MatchState:
    """Неизменяемый снимок партии `Match`, отдаваемый `Match.state`.

    Содержит скрытое внутри стадии (раскладки, содержимое ряда). Что из
    этого видит конкретный игрок, решают правила (см.
    docs/rules/visibility.md).

    - `turn_circle`  — очередь хода по кругу.
    - `active`       — чей сейчас ход.
    - `turn_number`  — номер хода в партии.
    - `seats`        — снимки мест.
    - `stage`        — снимок текущей стадии: подготовки или раунда.
    """

    turn_circle: tuple[PlayerID, ...]
    active: PlayerID
    turn_number: int
    seats: frozendict[PlayerID, SeatState]
    stage: PreparationState | RoundState
