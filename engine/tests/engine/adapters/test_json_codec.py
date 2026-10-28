"""JSON по проводу: строгий разбор, фаззинг разбора, сборка всего исходящего."""

import json
from contextlib import suppress
from random import Random

import pytest

from engine.adapters.json_codec import BadRequest, decode, encode
from engine.core.application.ports import ClientID
from engine.core.application.table import AskSnapshot, Resume, Table
from engine.core.domain.catalog import Item
from engine.core.domain.commands import (
    ChangeSettings,
    Join,
    Prepare,
    Shoot,
    Take,
    UseItem,
)
from engine.core.domain.state import Finished, InProgress, Settings
from tests.engine.core.domain.test_random_games import (
    game_command,
    lobby_command,
)


@pytest.mark.parametrize(
    ("text", "request_"),
    [
        ('{"type": "join"}', Join()),
        ('{"type": "shoot", "chamber": 3, "target": 2}', Shoot(3, 2)),
        (
            '{"type": "use_item", "item": "share", '
            '"player": 2, "take": "chip"}',
            UseItem(Item.SHARE, player=2, take=Take.CHIP),
        ),
        (
            '{"type": "prepare", "hand": ["water", "water"], "chips": [0, 2]}',
            Prepare((Item.WATER, Item.WATER), (0, 2)),
        ),
        (
            '{"type": "change_settings", "settings": {"rounds": 5, '
            '"health": [2, 3], "excluded": ["shield"]}}',
            ChangeSettings(
                Settings(
                    rounds=5,
                    health=(2, 3),
                    excluded=frozenset({Item.SHIELD}),
                )
            ),
        ),
        ('{"type": "resume", "token": "abc"}', Resume("abc")),
        ('{"type": "snapshot"}', AskSnapshot()),
    ],
)
def test_requests_parse(text, request_):
    assert decode(text) == request_


@pytest.mark.parametrize(
    "text",
    [
        "not json",
        "[1, 2]",
        '{"chamber": 1}',
        '{"type": "teleport"}',
        '{"type": "join", "extra": 1}',
        '{"type": "shoot", "chamber": 1}',
        '{"type": "shoot", "chamber": true, "target": 2}',
        '{"type": "shoot", "chamber": 1.5, "target": 2}',
        '{"type": "use_item", "item": "laser"}',
        '{"type": "prepare", "hand": "water", "chips": []}',
        '{"type": "change_settings", "settings": {"health": [2]}}',
        '{"type": "change_settings", "settings": {"cheat": 1}}',
    ],
    ids=[
        "not json",
        "not object",
        "no type",
        "unknown type",
        "extra field",
        "missing field",
        "bool as int",
        "float as int",
        "unknown item",
        "string as list",
        "short pair",
        "unknown setting",
    ],
)
def test_malformed_requests_are_rejected(text):
    with pytest.raises(BadRequest):
        decode(text)


def random_json(rng: Random, depth: int = 0):
    kinds = ["int", "str", "bool", "null", "float"]
    if depth < 3:
        kinds += ["list", "dict"]
    match rng.choice(kinds):
        case "int":
            return rng.choice([0, 1, -1, 3, 10**30, -(10**30)])
        case "str":
            return rng.choice(["", "join", "shoot", "water", "chip", "type"])
        case "bool":
            return rng.random() < 0.5
        case "null":
            return None
        case "float":
            return rng.choice([0.5, -1e308, float("inf")])
        case "list":
            return [
                random_json(rng, depth + 1) for _ in range(rng.randint(0, 3))
            ]
        case _:
            return {
                rng.choice(
                    [
                        "type",
                        "chamber",
                        "target",
                        "item",
                        "hand",
                        "chips",
                        "settings",
                        "health",
                        "token",
                        "x",
                    ]
                ): random_json(rng, depth + 1)
                for _ in range(rng.randint(0, 4))
            }


TYPES = [
    "join",
    "leave",
    "start",
    "change_settings",
    "prepare",
    "shoot",
    "use_item",
    "resume",
    "snapshot",
    "history",
]


def test_fuzzed_input_never_breaks_the_parser():
    rng = Random(0)
    for _ in range(20000):
        data = random_json(rng)
        if isinstance(data, dict) and rng.random() < 0.7:
            data["type"] = rng.choice(TYPES)
        with suppress(BadRequest):
            decode(json.dumps(data))


class Wire:
    """Отправитель, который сразу кодирует всё в JSON."""

    def __init__(self) -> None:
        self.sent: list[dict] = []

    def send(self, client, out) -> None:
        self.sent.append(json.loads(encode(out)))


class Clock:
    def start(self, key, delay, callback) -> None:
        pass

    def cancel(self, key) -> None:
        pass


def test_everything_the_table_sends_encodes_to_json():
    for seed in range(20):
        rng = Random(seed)
        wire = Wire()
        table = Table(wire, Clock(), rng)
        seats = rng.randint(2, 6)
        for c in range(1, seats + 1):
            table.connect(ClientID(c))
        for _ in range(3000):
            game = table._game
            if isinstance(game, Finished):
                break
            if isinstance(game, InProgress):
                actor, cmd = game_command(game, rng)
            else:
                actor, cmd = lobby_command(game, seats, rng)
            table.receive(ClientID(actor), cmd)
        assert isinstance(table._game, Finished), f"seed {seed}"
        assert all("type" in out for out in wire.sent)
