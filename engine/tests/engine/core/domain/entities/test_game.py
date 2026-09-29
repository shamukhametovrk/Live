"""Инварианты игры `Game`: лобби, присутствие, смена партий, конец."""

from collections.abc import Sequence

import pytest

from engine.core.domain.entities import Game, Match, Preparation, Seat
from engine.core.domain.enums import GameStage, Presence
from engine.core.domain.exceptions import DomainError
from engine.core.domain.exceptions.game import (
    GameError,
    GameLobbyError,
    GameSettingsError,
    GameStageError,
)
from engine.core.domain.ids import PlayerID
from engine.core.domain.value_objects import (
    GameSettings,
    GameState,
    MatchState,
    RoundConfig,
)

A, B, C, D = PlayerID(1), PlayerID(2), PlayerID(3), PlayerID(4)
CONFIG = RoundConfig(chambers=4, cartridges=1, layers=(1,))


def make_match(players: Sequence[PlayerID], first: PlayerID) -> Match:
    seats = {p: Seat(max_items=2, health_points=3) for p in players}
    preparation = Preparation(CONFIG, set(players), {p: () for p in players})
    return Match(seats, players, first, preparation)


def lobby(*players: PlayerID) -> Game:
    game = Game()
    for player in players:
        game.join(player)
    return game


def started(*players: PlayerID, matches: int = 3) -> Game:
    game = lobby(*players)
    game.settings = GameSettings(matches=matches)
    game.start_match(make_match(players, players[0]))
    return game


def end_current_match(game: Game, winner: PlayerID) -> None:
    """Все, кроме победителя, гибнут в текущей партии."""
    for player in game.match.turn_circle:
        if player != winner:
            game.match.seat(player).health_points = 0


def withdraw(game: Game, player: PlayerID) -> None:
    game.disconnect(player)
    game.withdraw(player)


# --------------------------------------------------------------------------- #
# Лобби
# --------------------------------------------------------------------------- #


def test_new_game_is_an_empty_lobby() -> None:
    game = Game()

    assert game.stage is GameStage.LOBBY
    assert game.settings == GameSettings()
    assert game.host is None
    assert game.players == ()
    assert game.remaining == ()
    assert game.matches_played == 0
    assert not game.anyone_away
    with pytest.raises(ValueError):
        _ = game.match


def test_first_joined_becomes_host() -> None:
    game = lobby(B, A, C)
    assert game.host == B
    assert game.players == (B, A, C)


def test_join_twice_rejected() -> None:
    game = lobby(A)
    with pytest.raises(GameLobbyError):
        game.join(A)
    assert game.players == (A,)


def test_seventh_player_rejected() -> None:
    game = lobby(*(PlayerID(i) for i in range(1, 7)))
    with pytest.raises(GameLobbyError):
        game.join(PlayerID(7))
    assert len(game.players) == 6


def test_settings_can_be_changed_in_lobby_many_times() -> None:
    game = lobby(A)
    game.settings = GameSettings(matches=1)
    game.settings = GameSettings(matches=5, max_items=2)
    assert game.settings == GameSettings(matches=5, max_items=2)


def test_leave_removes_player() -> None:
    game = lobby(A, B, C)
    game.leave(B)
    assert game.players == (A, C)


def test_host_cannot_leave() -> None:
    game = lobby(A, B)
    with pytest.raises(ValueError) as info:
        game.leave(A)
    assert not isinstance(info.value, DomainError)
    assert game.players == (A, B)


def test_leave_of_unknown_player_is_engine_bug() -> None:
    with pytest.raises(ValueError):
        lobby(A).leave(B)


def test_presence_does_not_exist_in_lobby() -> None:
    with pytest.raises(ValueError):
        lobby(A).presence(A)


def test_first_moves_are_zero_in_lobby() -> None:
    game = lobby(A)
    assert game.first_moves(A) == 0
    with pytest.raises(ValueError):
        game.first_moves(B)


# --------------------------------------------------------------------------- #
# Старт
# --------------------------------------------------------------------------- #


def test_start_moves_to_first_match() -> None:
    game = lobby(A, B, C)
    match = make_match((A, B, C), first=B)
    game.start_match(match)

    assert game.stage is GameStage.IN_MATCH
    assert game.match is match
    assert game.matches_played == 0
    assert all(game.presence(p) is Presence.PRESENT for p in (A, B, C))
    assert [game.first_moves(p) for p in (A, B, C)] == [0, 1, 0]


def test_start_with_one_player_is_engine_bug() -> None:
    game = lobby(A)
    with pytest.raises(ValueError):
        game.start_match(make_match((A, B), first=A))
    assert game.stage is GameStage.LOBBY


def test_first_match_must_include_all_players() -> None:
    game = lobby(A, B, C)
    with pytest.raises(ValueError):
        game.start_match(make_match((A, B), first=A))
    assert game.stage is GameStage.LOBBY


def test_after_start_lobby_actions_rejected() -> None:
    game = started(A, B)

    with pytest.raises(GameStageError):
        game.join(C)
    with pytest.raises(GameStageError):
        game.settings = GameSettings(matches=1)
    with pytest.raises(ValueError):
        game.leave(B)


# --------------------------------------------------------------------------- #
# Присутствие
# --------------------------------------------------------------------------- #


def test_disconnect_and_reconnect() -> None:
    game = started(A, B)
    game.disconnect(B)
    assert game.presence(B) is Presence.AWAY
    assert game.anyone_away

    game.reconnect(B)
    assert game.presence(B) is Presence.PRESENT
    assert not game.anyone_away


def test_withdraw_removes_from_remaining_but_does_not_kill() -> None:
    game = started(A, B, C)
    withdraw(game, B)

    assert game.presence(B) is Presence.WITHDRAWN
    assert game.remaining == (A, C)
    assert game.match.seat(B).is_alive


@pytest.mark.parametrize(
    "steps",
    [
        ("reconnect",),
        ("withdraw",),
        ("disconnect", "disconnect"),
        ("disconnect", "withdraw", "reconnect"),
        ("disconnect", "withdraw", "disconnect"),
        ("disconnect", "withdraw", "withdraw"),
    ],
    ids=[
        "reconnect-present",
        "withdraw-present",
        "disconnect-away",
        "reconnect-withdrawn",
        "disconnect-withdrawn",
        "withdraw-withdrawn",
    ],
)
def test_invalid_presence_transition_is_engine_bug(
    steps: tuple[str, ...],
) -> None:
    game = started(A, B)
    *prefix, last = steps
    for step in prefix:
        getattr(game, step)(B)
    before = game.presence(B)

    with pytest.raises(ValueError) as info:
        getattr(game, last)(B)
    assert not isinstance(info.value, DomainError)
    assert game.presence(B) is before


def test_presence_of_unknown_player_is_engine_bug() -> None:
    game = started(A, B)
    with pytest.raises(ValueError):
        game.disconnect(C)


# --------------------------------------------------------------------------- #
# Следующая партия
# --------------------------------------------------------------------------- #


def test_next_match_counts_the_previous_one() -> None:
    game = started(A, B, C)
    end_current_match(game, winner=A)
    match = make_match((A, B, C), first=C)
    game.start_match(match)

    assert game.match is match
    assert game.matches_played == 1
    assert [game.first_moves(p) for p in (A, B, C)] == [1, 0, 1]


def test_next_match_while_current_goes_on_is_engine_bug() -> None:
    game = started(A, B, C)
    with pytest.raises(ValueError):
        game.start_match(make_match((A, B, C), first=B))
    assert game.matches_played == 0


def test_next_match_excludes_withdrawn() -> None:
    game = started(A, B, C)
    withdraw(game, C)
    end_current_match(game, winner=A)

    with pytest.raises(ValueError):
        game.start_match(make_match((A, B, C), first=B))
    game.start_match(make_match((A, B), first=B))
    assert set(game.match.turn_circle) == {A, B}


def test_next_match_when_all_played_is_engine_bug() -> None:
    game = started(A, B, matches=1)
    end_current_match(game, winner=A)

    with pytest.raises(ValueError):
        game.start_match(make_match((A, B), first=B))
    assert game.matches_played == 0


def test_next_match_with_too_few_remaining_is_engine_bug() -> None:
    game = started(A, B)
    withdraw(game, B)
    end_current_match(game, winner=A)

    with pytest.raises(ValueError):
        game.start_match(make_match((A, B), first=A))


# --------------------------------------------------------------------------- #
# Конец игры
# --------------------------------------------------------------------------- #


def test_finish_after_last_match() -> None:
    game = started(A, B, matches=1)
    end_current_match(game, winner=B)
    game.finish()

    assert game.stage is GameStage.FINISHED
    assert game.matches_played == 1
    with pytest.raises(ValueError):
        _ = game.match


def test_early_finish_when_too_few_remain() -> None:
    game = started(A, B, C, matches=5)
    withdraw(game, B)
    withdraw(game, C)
    end_current_match(game, winner=A)
    game.finish()

    assert game.stage is GameStage.FINISHED
    assert game.matches_played == 1


def test_finish_while_match_goes_on_is_engine_bug() -> None:
    game = started(A, B, matches=1)
    with pytest.raises(ValueError):
        game.finish()
    assert game.stage is GameStage.IN_MATCH


def test_finish_with_matches_left_is_engine_bug() -> None:
    game = started(A, B, matches=2)
    end_current_match(game, winner=A)
    with pytest.raises(ValueError):
        game.finish()
    assert game.stage is GameStage.IN_MATCH


def test_finish_from_lobby_is_engine_bug() -> None:
    with pytest.raises(ValueError):
        lobby(A, B).finish()


def test_nothing_starts_after_finish() -> None:
    game = started(A, B, matches=1)
    end_current_match(game, winner=A)
    game.finish()

    with pytest.raises(ValueError):
        game.start_match(make_match((A, B), first=A))


def test_presence_still_changes_after_finish() -> None:
    game = started(A, B, matches=1)
    end_current_match(game, winner=A)
    game.finish()

    game.disconnect(B)
    assert game.presence(B) is Presence.AWAY


# --------------------------------------------------------------------------- #
# Снимок
# --------------------------------------------------------------------------- #


def test_state_in_lobby() -> None:
    state = lobby(A, B).state

    assert isinstance(state, GameState)
    assert state.stage is GameStage.LOBBY
    assert state.host == A
    assert state.players == (A, B)
    assert dict(state.presence) == {}
    assert state.match is None


def test_state_in_match() -> None:
    game = started(A, B)
    game.disconnect(B)
    state = game.state

    assert state.stage is GameStage.IN_MATCH
    assert dict(state.presence) == {A: Presence.PRESENT, B: Presence.AWAY}
    assert dict(state.first_moves) == {A: 1, B: 0}
    assert isinstance(state.match, MatchState)


def test_state_is_detached_from_later_changes() -> None:
    game = started(A, B)
    snapshot = game.state
    game.disconnect(B)

    assert snapshot.presence[B] is Presence.PRESENT


# --------------------------------------------------------------------------- #
# Исключения
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "error", [GameStageError, GameLobbyError, GameSettingsError]
)
def test_game_errors_are_domain_errors(error: type[Exception]) -> None:
    assert issubclass(error, GameError)
    assert issubclass(error, DomainError)
