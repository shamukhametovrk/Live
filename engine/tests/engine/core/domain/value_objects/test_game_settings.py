"""Настройки хоста `GameSettings`: значения по умолчанию и допустимые."""

import dataclasses

import pytest

from engine.core.domain.enums import Item
from engine.core.domain.exceptions.game import GameSettingsError
from engine.core.domain.value_objects import GameSettings


def test_defaults_match_the_rules() -> None:
    """Значения из таблицы по умолчанию в docs/rules/game.md."""
    settings = GameSettings()

    assert settings.matches == 3
    assert settings.allowed_items == frozenset(Item)
    assert settings.max_items == 8
    assert settings.min_health == 1
    assert settings.max_health == 5


@pytest.mark.parametrize(
    "overrides",
    [
        {"matches": 1},
        {"max_items": 0},
        {"min_health": 1, "max_health": 1},
        {"allowed_items": frozenset()},
    ],
    ids=["one-match", "no-items-in-hand", "equal-health", "no-items-allowed"],
)
def test_boundary_values_accepted(overrides: dict[str, object]) -> None:
    GameSettings(**overrides)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "overrides",
    [
        {"matches": 0},
        {"max_items": -1},
        {"min_health": 0},
        {"min_health": 4, "max_health": 3},
    ],
    ids=["no-matches", "negative-hand", "zero-health", "min-above-max"],
)
def test_invalid_settings_rejected(overrides: dict[str, object]) -> None:
    with pytest.raises(GameSettingsError):
        GameSettings(**overrides)  # type: ignore[arg-type]


def test_frozen_and_equal_by_value() -> None:
    settings = GameSettings(matches=2)
    assert settings == GameSettings(matches=2)
    assert len({settings, GameSettings(matches=2)}) == 1
    with pytest.raises(dataclasses.FrozenInstanceError):
        settings.matches = 4  # type: ignore[misc]
