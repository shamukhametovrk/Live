"""Сквозной прогон: настоящий движок на свободном порту, боты — до конца."""

import asyncio
import random
import socket
import subprocess
import time
from pathlib import Path

import pytest

from tools.net_bot import play

ENGINE = Path(__file__).parents[3]


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def engine_url():
    port = free_port()
    server = subprocess.Popen(
        [
            "uv",
            "run",
            "uvicorn",
            "engine.adapters.websocket:create_app",
            "--factory",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        cwd=ENGINE,
    )
    try:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            with socket.socket() as s:
                if s.connect_ex(("127.0.0.1", port)) == 0:
                    break
            time.sleep(0.2)
        else:
            pytest.fail("engine did not start")
        yield f"ws://127.0.0.1:{port}/ws"
    finally:
        server.terminate()
        server.wait(10)


@pytest.mark.parametrize("seed", range(3))
def test_bots_play_a_whole_game_over_websocket(engine_url, seed):
    rng = random.Random(seed)

    async def game():
        bots = [
            play(engine_url, random.Random(rng.random()), 3 if i == 0 else None)
            for i in range(3)
        ]
        return await asyncio.wait_for(asyncio.gather(*bots), timeout=60)

    finals = asyncio.run(game())
    assert all(f["type"] == "finished" for f in finals)
    assert finals[0] == finals[1] == finals[2]
    assert finals[0]["results"]
