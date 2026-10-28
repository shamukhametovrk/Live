"""WebSocket-адаптер: настоящие сокеты в памяти, тестовый клиент FastAPI."""

import asyncio
from random import Random

from fastapi.testclient import TestClient

from engine.adapters.websocket import AsyncioTimer, create_app


def receive_until(socket, kind: str) -> dict:
    while True:
        data = socket.receive_json()
        if data["type"] == kind:
            return data


def test_connect_join_and_play_over_json():
    client = TestClient(create_app(Random(0)))
    with (
        client.websocket_connect("/ws") as a,
        client.websocket_connect("/ws") as b,
    ):
        assert a.receive_json() == {"type": "welcome", "client": 1}
        assert a.receive_json() == {"type": "snapshot", "view": None}
        a.send_json({"type": "join"})
        assert receive_until(a, "token")["token"]
        b.send_json({"type": "join"})
        receive_until(b, "token")
        a.send_json({"type": "start"})
        started = receive_until(b, "message")
        while started["message"]["type"] != "spread_started":
            started = receive_until(b, "message")
        assert set(started["message"]) == {"type", "size", "offer"}


def test_garbage_is_rejected_and_connection_lives_on():
    client = TestClient(create_app(Random(0)))
    with client.websocket_connect("/ws") as a:
        receive_until(a, "snapshot")
        a.send_text("{not json")
        assert a.receive_json() == {"type": "rejected", "code": "bad_request"}
        a.send_json({"type": "join"})
        assert receive_until(a, "token")


def test_dropped_player_pauses_game_and_returns_by_token():
    client = TestClient(create_app(Random(0)))
    with client.websocket_connect("/ws") as a:
        a.send_json({"type": "join"})
        with client.websocket_connect("/ws") as b:
            b.send_json({"type": "join"})
            token = receive_until(b, "token")["token"]
            a.send_json({"type": "start"})
            receive_until(b, "message")
        lost = receive_until(a, "message")
        while lost["message"]["type"] != "disconnected":
            lost = receive_until(a, "message")
        assert lost["message"]["player"] == 2
        with client.websocket_connect("/ws") as b2:
            assert receive_until(b2, "snapshot")["view"] is None  # чужой
            b2.send_json({"type": "resume", "token": token})
            back = receive_until(a, "message")
            assert back["message"] == {"type": "reconnected", "player": 2}
            assert receive_until(b2, "snapshot")["view"]["type"] == "game_view"


def test_asyncio_timer_fires_and_cancels():
    async def scenario() -> list[str]:
        fired: list[str] = []
        timer = AsyncioTimer()
        timer.start("a", 0.01, lambda: fired.append("a"))
        timer.start("b", 0.01, lambda: fired.append("b"))
        timer.cancel("b")
        await asyncio.sleep(0.05)
        return fired

    assert asyncio.run(scenario()) == ["a"]


def test_engine_serves_the_web_client():
    client = TestClient(create_app(Random(0)))
    page = client.get("/")
    assert page.status_code == 200 and "<title>Live</title>" in page.text
    assert client.get("/net.js").status_code == 200
