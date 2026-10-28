"""Порты прикладного слоя: что столу нужно снаружи.

Адаптеры реализуют их на WebSocket и asyncio, тесты — заглушками.
"""

from collections.abc import Callable, Hashable
from dataclasses import dataclass
from typing import NewType, Protocol

from ..domain.events import Event
from ..domain.messages import Message
from ..domain.view import View

ClientID = NewType("ClientID", int)
"""Номер соединения. Севший за стол клиент — игрок с тем же номером."""


# Исходящее


@dataclass(frozen=True, slots=True)
class Welcome:
    client: ClientID


@dataclass(frozen=True, slots=True)
class TokenIssued:
    token: str


@dataclass(frozen=True, slots=True)
class Snapshot:
    view: View | None


@dataclass(frozen=True, slots=True)
class Delivered:
    message: Message


@dataclass(frozen=True, slots=True)
class Rejected:
    code: str


@dataclass(frozen=True, slots=True)
class History:
    events: tuple[Event, ...]


type Outgoing = (
    Welcome | TokenIssued | Snapshot | Delivered | Rejected | History
)


class Sender(Protocol):
    def send(self, client: ClientID, out: Outgoing) -> None:
        """Доставить клиенту, не дожидаясь, пока он прочтёт."""
        ...


class Timer(Protocol):
    def start(
        self, key: Hashable, delay: float, callback: Callable[[], None]
    ) -> None:
        """Через `delay` секунд вызвать `callback`; ключ заменяет прежний."""
        ...

    def cancel(self, key: Hashable) -> None:
        """Отменить таймер по ключу, если он есть."""
        ...
