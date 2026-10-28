"""Стол: кто что получает, связь, токены. Без сети и без настоящего времени."""

from random import Random

from engine.core.application.ports import (
    ClientID,
    Delivered,
    History,
    Rejected,
    Snapshot,
    TokenIssued,
    Welcome,
)
from engine.core.application.table import AskHistory, AskSnapshot, Resume, Table
from engine.core.domain import parameters
from engine.core.domain.commands import Join, Leave, Prepare, Shoot, Start
from engine.core.domain.messages import (
    Cancelled,
    Disconnected,
    GameStarted,
    Joined,
    Reconnected,
    SpreadStarted,
    Withdrew,
)
from engine.core.domain.state import InProgress, Lobby
from engine.core.domain.view import GameView

A, B, C = ClientID(1), ClientID(2), ClientID(3)


class Outbox:
    def __init__(self) -> None:
        self.sent: dict[ClientID, list] = {}

    def send(self, client, out) -> None:
        self.sent.setdefault(client, []).append(out)

    def take(self, client) -> list:
        return self.sent.pop(client, [])

    def messages(self, client) -> list:
        return [
            o.message for o in self.take(client) if isinstance(o, Delivered)
        ]


class Clock:
    def __init__(self) -> None:
        self.timers: dict = {}

    def start(self, key, delay, callback) -> None:
        self.timers[key] = (delay, callback)

    def cancel(self, key) -> None:
        self.timers.pop(key, None)

    def fire(self, key) -> None:
        _, callback = self.timers.pop(key)
        callback()


def table_with(*clients):
    out, clock = Outbox(), Clock()
    table = Table(out, clock, Random(0))
    for c in clients:
        table.connect(c)
    return table, out, clock


def seated(*clients):
    table, out, clock = table_with(*clients)
    tokens = {}
    for c in clients:
        table.receive(c, Join())
        tokens[c] = next(
            o.token for o in out.sent[c] if isinstance(o, TokenIssued)
        )
    for c in clients:
        out.take(c)
    return table, out, clock, tokens


def test_connect_greets_and_join_issues_token_and_snapshot():
    table, out, _ = table_with(A, B)
    assert out.take(A) == [Welcome(A), Snapshot(None)]
    out.take(B)
    table.receive(A, Join())
    sent = out.take(A)
    assert Delivered(Joined(1)) in sent
    assert any(isinstance(o, TokenIssued) for o in sent)
    assert isinstance(sent[-1], Snapshot) and isinstance(sent[-1].view, Lobby)
    assert out.messages(B) == [Joined(1)]


def test_players_get_only_their_own_offer():
    table, out, _, _ = seated(A, B)
    table.receive(A, Start())
    offers = {
        c: next(m for m in out.messages(c) if isinstance(m, SpreadStarted))
        for c in (A, B)
    }
    game = table._game
    assert offers[A].offer == game.round.spread.offers[1]
    assert offers[B].offer == game.round.spread.offers[2]


def test_rejection_goes_only_to_sender():
    table, out, _, _ = seated(A, B)
    table.receive(B, Start())
    assert out.take(B) == [Rejected("not_host")]
    assert out.take(A) == []


def test_unseated_client_cannot_act_and_sees_lobby_until_start():
    table, out, _, _ = seated(A, B)
    table.connect(C)
    out.take(C)
    table.receive(C, Shoot(0, 1))
    assert out.take(C) == [Rejected("not_joined")]
    table.receive(A, Start())
    assert out.messages(C) == [GameStarted((1, 2))]
    table.receive(C, AskSnapshot())
    assert out.take(C) == [Snapshot(None)]


def test_lost_connection_pauses_and_times_out():
    table, out, clock, _ = seated(A, B)
    table.receive(A, Start())
    out.take(A)
    table.disconnect(B)
    assert out.messages(A) == [Disconnected(2)]
    delay, _ = clock.timers[2]
    assert delay == parameters.RECONNECT_WAIT
    clock.fire(2)
    assert Withdrew(2) in out.messages(A)


def test_resume_by_token_restores_player_and_cancels_timer():
    table, out, clock, tokens = seated(A, B)
    table.receive(A, Start())
    table.disconnect(B)
    out.take(A)
    table.connect(C)
    out.take(C)
    table.receive(C, Resume(tokens[B]))
    assert 2 not in clock.timers
    assert out.messages(A) == [Reconnected(2)]
    sent = out.take(C)
    assert isinstance(sent[-1].view, GameView)
    size = table._game.round.spread.size
    table.receive(C, Prepare((), (0,) * size))
    assert not any(isinstance(o, Rejected) for o in out.take(C))


def test_bad_token_is_rejected_and_fresh_connection_takes_over():
    table, out, _, tokens = seated(A, B)
    table.connect(C)
    out.take(C)
    table.receive(C, Resume("nope"))
    assert out.take(C) == [Rejected("bad_token")]
    table.receive(C, Resume(tokens[A]))  # A ещё «жив», но C забирает игрока
    table.receive(C, Start())
    assert isinstance(table._game, InProgress)
    table.receive(A, Leave())
    assert out.take(A)[-1] == Rejected("not_joined")


def test_host_leaving_cancels_and_voids_tokens():
    table, out, _, tokens = seated(A, B)
    table.receive(A, Leave())
    assert out.messages(B) == [Cancelled()]
    table.receive(B, Resume(tokens[B]))
    assert out.take(B) == [Rejected("bad_token")]


def test_history_only_after_finish():
    table, out, _, _ = seated(A, B)
    table.receive(A, AskHistory())
    assert out.take(A) == [Rejected("game_not_finished")]
    table.receive(A, Start())
    table.disconnect(B)
    table._timer.fire(2)  # B выбыл — игроков меньше двух, игра окончена
    out.take(A)
    table.receive(A, AskHistory())
    (history,) = out.take(A)
    assert isinstance(history, History) and history.events[0] == Joined(1)


def test_table_empties_after_finish_and_a_new_game_can_gather():
    table, out, clock, tokens = seated(A, B)
    table.receive(A, Start())
    table.disconnect(B)
    clock.fire(2)  # B выбыл — игра окончена
    delay, _ = clock.timers["reset"]
    assert delay == parameters.RESET_WAIT
    out.take(A)
    clock.fire("reset")
    assert out.take(A) == [Snapshot(None)]
    table.receive(A, Resume(tokens[A]))
    assert out.take(A) == [Rejected("bad_token")]
    table.connect(B)
    for c in (A, B):
        table.receive(c, Join())
    assert isinstance(table._game, Lobby) and table._game.players == (1, 2)
