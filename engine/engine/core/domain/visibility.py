"""Видимость: что из состояния и событий знает конкретный игрок.

Таблица «кто что видит» из docs/rules/visibility.md переходит в код
здесь и только здесь (решение 0013).
"""

from . import events as e
from . import messages as m
from .ids import PlayerID
from .state import Game, InProgress, Preparing
from .view import (
    ChamberView,
    GameView,
    PreparingView,
    RoundView,
    ShootingView,
    View,
)


def view(game: Game, me: PlayerID) -> View:
    """Снимок игры для игрока `me`."""
    if not isinstance(game, InProgress):
        return game
    round_ = game.round
    spread = round_.spread
    if isinstance(spread, Preparing):
        shown = PreparingView(
            spread.size, spread.offers.get(me, ()), frozenset(spread.choices)
        )
    else:
        weights = spread.weights
        shown = ShootingView(
            chambers=tuple(
                ChamberView(c.used, c.loaded if c.used else None)
                for c in spread.chambers
            ),
            chips=spread.chips.get(me),
            announced=spread.announced,
            seen=frozendict(
                {i: weights[i] for i in sorted(spread.revealed.get(me, ()))}
            ),
        )
    return GameView(
        settings=game.settings,
        players=game.players,
        presence=game.presence,
        results=game.results,
        round=RoundView(
            round_.start_health,
            round_.circle,
            round_.first,
            round_.active,
            round_.turn,
            round_.seats,
            shown,
        ),
    )


def project(event: e.Event, me: PlayerID) -> m.Message:
    """Что игрок `me` узнаёт из события."""
    match event:
        case e.SpreadStarted(size, offers):
            return m.SpreadStarted(size, offers.get(me, ()))
        case e.Loaded(offers, hands, chips, _, announced):
            return m.Loaded(offers, hands, chips.get(me), announced)
        case e.WeightSeen(actor, chamber, weight):
            return m.WeightSeen(actor, chamber, weight if actor == me else None)
        case e.WeightsSeen(actor, weights):
            return m.WeightsSeen(actor, weights if actor == me else None)
        case e.Reversed(actor, chamber, _):
            return m.Reversed(actor, chamber)
        case e.CartridgeAdded(actor, _):
            return m.CartridgeAdded(actor)
        case e.CartridgeRemoved(actor, _):
            return m.CartridgeRemoved(actor)
        case e.Shaken(actor, _):
            return m.Shaken(actor)
        case _:
            return event
