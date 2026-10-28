"""WebSocket-адаптер на FastAPI (см. docs/engine/architecture/adapters).

Реализует порты стола: отправитель — очередь на соединение и задача,
которая пишет её в сокет; таймер — `loop.call_later`. Заодно отдаёт
веб-клиент (папка `web/`) на `/`.

Запуск:  uv run uvicorn engine.adapters.websocket:create_app --factory
"""

import asyncio
import itertools
from collections.abc import Callable, Hashable
from pathlib import Path
from random import Random

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from starlette.types import Scope

from ..core.application.ports import ClientID, Outgoing, Rejected
from ..core.application.table import Table
from .json_codec import BadRequest, decode, encode

WEB = Path(__file__).parents[2] / "web"


class QueueSender:
    """Отправитель: у каждого соединения своя очередь.

    Медленный клиент копит свою очередь и не тормозит остальных.
    """

    def __init__(self) -> None:
        self._queues: dict[ClientID, asyncio.Queue[str]] = {}

    def open(self, client: ClientID) -> asyncio.Queue[str]:
        queue: asyncio.Queue[str] = asyncio.Queue()
        self._queues[client] = queue
        return queue

    def close(self, client: ClientID) -> None:
        self._queues.pop(client, None)

    def send(self, client: ClientID, out: Outgoing) -> None:
        queue = self._queues.get(client)
        if queue is not None:
            queue.put_nowait(encode(out))


class FreshStaticFiles(StaticFiles):
    """Статика, которую браузер сверяет с сервером при каждой загрузке.

    Без этого после обновления движка браузер берёт часть скриптов из
    кэша и смешивает старый клиент с новым.
    """

    async def get_response(self, path: str, scope: Scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache"
        return response


class AsyncioTimer:
    def __init__(self) -> None:
        self._handles: dict[Hashable, asyncio.TimerHandle] = {}

    def start(
        self, key: Hashable, delay: float, callback: Callable[[], None]
    ) -> None:
        self.cancel(key)
        loop = asyncio.get_running_loop()
        self._handles[key] = loop.call_later(delay, self._fire, key, callback)

    def cancel(self, key: Hashable) -> None:
        handle = self._handles.pop(key, None)
        if handle is not None:
            handle.cancel()

    def _fire(self, key: Hashable, callback: Callable[[], None]) -> None:
        self._handles.pop(key, None)
        callback()


def create_app(rng: Random | None = None) -> FastAPI:
    sender = QueueSender()
    table = Table(sender, AsyncioTimer(), rng or Random())
    numbers = itertools.count(1)
    app = FastAPI(title="Live engine")

    @app.websocket("/ws")
    async def connection(socket: WebSocket) -> None:
        await socket.accept()
        client = ClientID(next(numbers))
        writer = asyncio.create_task(_write(socket, sender.open(client)))
        table.connect(client)
        try:
            while True:
                text = await socket.receive_text()
                try:
                    request = decode(text)
                except BadRequest:
                    sender.send(client, Rejected("bad_request"))
                    continue
                table.receive(client, request)
        except WebSocketDisconnect:
            pass
        finally:
            table.disconnect(client)
            sender.close(client)
            writer.cancel()

    app.mount("/", FreshStaticFiles(directory=WEB, html=True), name="web")
    return app


async def _write(socket: WebSocket, queue: asyncio.Queue[str]) -> None:
    while True:
        await socket.send_text(await queue.get())
