"""Эталонная картина мира: применить сообщение к снимку.

Так клиент собирает игру из сообщений. Здесь это не код клиента, а
эталон для теста «снимок + сообщения = снимок»: если он зелёный,
сообщений достаточно, чтобы любой клиент собрал правильную картину.
"""

from dataclasses import replace
from typing import assert_never

from engine.core.domain.catalog import Item
from engine.core.domain.ids import PlayerID
from engine.core.domain.messages import (
    Cancelled,
    CartridgeAdded,
    CartridgeRemoved,
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
    Loaded,
    Message,
    Passed,
    Peeked,
    Prepared,
    Reconnected,
    Reversed,
    RoundEnded,
    RoundStarted,
    SettingsChanged,
    Shaken,
    Shot,
    SpreadEnded,
    SpreadStarted,
    TurnPassed,
    Wasted,
    WeightSeen,
    WeightsSeen,
    Withdrew,
)
from engine.core.domain.state import (
    Double,
    Effect,
    Finished,
    FullForce,
    Lobby,
    PlayAlong,
    Presence,
    RoundResult,
    Seat,
    Shield,
    TryThis,
)
from engine.core.domain.view import (
    ChamberView,
    GameView,
    PreparingView,
    RoundView,
    ShootingView,
    View,
)

_EFFECT_ITEM: dict[type, Item] = {
    Double: Item.DOUBLE,
    FullForce: Item.FULL_FORCE,
    Shield: Item.SHIELD,
    PlayAlong: Item.PLAY_ALONG,
    TryThis: Item.TRY_THIS,
}


def apply(view: View | None, message: Message) -> View | None:
    """Снимок после сообщения."""
    match message:
        case Joined(p):
            if view is None:
                return Lobby(p, (p,), frozendict({p: Presence.PRESENT}))
            assert isinstance(view, Lobby)
            return replace(
                view,
                players=(*view.players, p),
                presence=view.presence | {p: Presence.PRESENT},
            )
        case Left(p):
            assert isinstance(view, Lobby)
            return replace(
                view,
                players=tuple(q for q in view.players if q != p),
                presence=frozendict(
                    {q: s for q, s in view.presence.items() if q != p}
                ),
            )
        case SettingsChanged(settings):
            assert isinstance(view, Lobby)
            return replace(view, settings=settings)
        case Cancelled():
            return None
        case Disconnected(p):
            return _presence(view, p, Presence.AWAY)
        case Reconnected(p):
            return _presence(view, p, Presence.PRESENT)
        case GameStarted(players):
            assert isinstance(view, Lobby)
            return GameView(view.settings, players, view.presence, (), None)
        case GameFinished():
            game = _game(view)
            return Finished(game.players, game.presence, game.results)
        case _:
            game = _game(view)
    match message:
        case Withdrew(p):
            game = _presence(game, p, Presence.WITHDRAWN)
            if game.round and p in game.round.seats:
                return _seat(game, p, health=0)
            return game
        case RoundStarted(health, circle, first):
            seats = frozendict({p: Seat(health) for p in circle})
            round_ = RoundView(health, circle, first, first, 1, seats, None)
            return replace(game, round=round_)
        case RoundEnded(winner):
            first = _round(game).first
            results = (*game.results, RoundResult(first, winner))
            return replace(game, results=results)
    round_ = _round(game)
    seats = dict(round_.seats)
    spread = round_.spread
    match message:
        case SpreadStarted(size, offer):
            spread = PreparingView(size, offer)
        case Prepared(p):
            assert isinstance(spread, PreparingView)
            spread = replace(spread, decided=spread.decided | {p})
        case Loaded(_, hands, chips, announced):
            assert isinstance(spread, PreparingView)
            for p, hand in hands.items():
                seats[p] = replace(seats[p], hand=hand, chips=0)
            spread = ShootingView(
                (ChamberView(),) * spread.size, chips, announced
            )
        case SpreadEnded() | Died():
            pass
        case Shot(_, chamber, target, loaded, damage):
            spread = _used(spread, chamber, loaded)
            seats[target] = _health(seats[target], -damage)
        case ChipEarned(p):
            seats[p] = replace(seats[p], chips=seats[p].chips + 1)
        case TurnPassed(active, turn):
            round_ = replace(round_, active=active, turn=turn)
        case EffectAdded(owner, effect):
            _spend(seats, round_.active, _EFFECT_ITEM[type(effect)])
            seats[owner] = _with_effects(
                seats[owner], (*seats[owner].effects, effect)
            )
        case EffectRemoved(owner, effect):
            kept = tuple(e for e in seats[owner].effects if e != effect)
            seats[owner] = _with_effects(seats[owner], kept)
        case WeightSeen(actor, chamber, weight):
            _spend(seats, actor, Item.ONE_EYE)
            if weight is not None:
                assert isinstance(spread, ShootingView)
                spread = replace(spread, seen=spread.seen | {chamber: weight})
        case WeightsSeen(actor, weights):
            _spend(seats, actor, Item.WIDE_EYES)
            if weights is not None:
                assert isinstance(spread, ShootingView)
                spread = replace(spread, seen=frozendict(enumerate(weights)))
        case Reversed(actor):
            _spend(seats, actor, Item.REVERSE)
        case CartridgeAdded(actor):
            _spend(seats, actor, Item.MORE)
        case CartridgeRemoved(actor):
            _spend(seats, actor, Item.SCARED)
        case Shaken(actor):
            _spend(seats, actor, Item.SHAKE)
        case Peeked(actor, chamber, loaded):
            _spend(seats, actor, Item.PEEK)
            spread = _used(spread, chamber, loaded)
        case Healed(actor, item, amount):
            _spend(seats, actor, item)
            seats[actor] = _health(seats[actor], amount)
        case Gambled(actor, _, amount):
            _spend(seats, actor, Item.DUBIOUS)
            seats[actor] = _health(seats[actor], amount)
        case Passed(actor):
            _spend(seats, actor, Item.PASS)
        case ItemStolen(actor, victim, item):
            _spend(seats, actor, Item.SHARE)
            _spend(seats, victim, item)
            seats[actor] = replace(
                seats[actor], hand=(*seats[actor].hand, item)
            )
        case ChipStolen(actor, victim):
            _spend(seats, actor, Item.SHARE)
            seats[victim] = replace(
                seats[victim], chips=seats[victim].chips - 1
            )
            seats[actor] = replace(seats[actor], chips=seats[actor].chips + 1)
        case Jackpot(actor):
            _spend(seats, actor, Item.JACKPOT)
            seats[actor] = replace(seats[actor], chips=seats[actor].chips + 3)
        case Wasted(actor, item):
            _spend(seats, actor, item)
        case _:
            assert_never(message)  # type: ignore[arg-type]
    round_ = replace(round_, seats=frozendict(seats), spread=spread)
    return replace(game, round=round_)


def _game(view: View | None) -> GameView:
    assert isinstance(view, GameView)
    return view


def _round(game: GameView) -> RoundView:
    assert game.round is not None
    return game.round


def _presence[V: (Lobby, GameView)](
    view: V | None, player: PlayerID, presence: Presence
) -> V:
    assert view is not None
    return replace(view, presence=view.presence | {player: presence})


def _seat(game: GameView, player: PlayerID, **changes) -> GameView:
    round_ = _round(game)
    seat = replace(round_.seats[player], **changes)
    seats = round_.seats | {player: seat}
    return replace(game, round=replace(round_, seats=seats))


def _spend(seats: dict[PlayerID, Seat], player: PlayerID, item: Item) -> None:
    hand = list(seats[player].hand)
    hand.remove(item)
    seats[player] = replace(seats[player], hand=tuple(hand))


def _health(seat: Seat, delta: int) -> Seat:
    return replace(seat, health=max(0, seat.health + delta))


def _with_effects(seat: Seat, effects: tuple[Effect, ...]) -> Seat:
    return replace(seat, effects=effects)


def _used(spread, chamber: int, loaded: bool) -> ShootingView:
    assert isinstance(spread, ShootingView)
    chambers = list(spread.chambers)
    chambers[chamber] = ChamberView(used=True, loaded=loaded)
    return replace(spread, chambers=tuple(chambers))
