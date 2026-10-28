"""JSON по проводу (см. docs/engine/architecture/adapters).

Сборка — общее правило для всего исходящего: класс → объект с `type` в
snake_case, перечисление → значение в нижнем регистре, кортеж → массив,
словарь → объект с ключами-строками.

Разбор строгий: неизвестный `type`, лишнее, недостающее или неверного
типа поле — `BadRequest`.
"""

import dataclasses
import json
import re
import types
import typing
from enum import Enum
from typing import Any

from ..core.application.ports import (
    Delivered,
    History,
    Outgoing,
    Rejected,
    Snapshot,
    TokenIssued,
    Welcome,
)
from ..core.application.table import AskHistory, AskSnapshot, Request, Resume
from ..core.domain.commands import (
    ChangeSettings,
    Join,
    Leave,
    Prepare,
    Shoot,
    Start,
    UseItem,
)


class BadRequest(Exception):
    """Входящее сообщение не разобрать."""


# Сборка


def encode(out: Outgoing) -> str:
    match out:
        case Welcome(client):
            data = {"type": "welcome", "client": client}
        case TokenIssued(token):
            data = {"type": "token", "token": token}
        case Snapshot(shown):
            data = {"type": "snapshot", "view": _plain(shown)}
        case Delivered(message):
            data = {"type": "message", "message": _plain(message)}
        case Rejected(code):
            data = {"type": "rejected", "code": code}
        case History(events):
            data = {"type": "history", "events": _plain(events)}
    return json.dumps(data, ensure_ascii=False)


def _plain(value: Any) -> Any:
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        data = {"type": _snake(type(value).__name__)}
        for f in dataclasses.fields(value):
            data[f.name] = _plain(getattr(value, f.name))
        return data
    if isinstance(value, Enum):
        return str(value.value if isinstance(value.value, str) else value.name)
    if isinstance(value, (tuple, list)):
        return [_plain(v) for v in value]
    if isinstance(value, (set, frozenset)):
        return sorted(_plain(v) for v in value)
    if isinstance(value, (dict, frozendict)):
        return {str(_plain(k)): _plain(v) for k, v in value.items()}
    return value


def _snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


# Разбор

_REQUESTS: dict[str, type] = {
    "join": Join,
    "leave": Leave,
    "start": Start,
    "change_settings": ChangeSettings,
    "prepare": Prepare,
    "shoot": Shoot,
    "use_item": UseItem,
    "resume": Resume,
    "snapshot": AskSnapshot,
    "history": AskHistory,
}


def decode(text: str | bytes) -> Request:
    try:
        data = json.loads(text)
    except (ValueError, RecursionError) as error:
        raise BadRequest("not_json") from error
    if not isinstance(data, dict) or not isinstance(data.get("type"), str):
        raise BadRequest("no_type")
    kind = _REQUESTS.get(data.pop("type"))
    if kind is None:
        raise BadRequest("unknown_type")
    return _object(kind, data)


def _object(kind: type, data: Any) -> Any:
    if not isinstance(data, dict):
        raise BadRequest("not_object")
    hints = typing.get_type_hints(kind)
    fields = {f.name: f for f in dataclasses.fields(kind)}
    if set(data) - set(fields):
        raise BadRequest("extra_field")
    values = {}
    for name, f in fields.items():
        if name in data:
            values[name] = _value(data[name], hints[name])
        elif (
            f.default is dataclasses.MISSING
            and f.default_factory is dataclasses.MISSING
        ):
            raise BadRequest("missing_field")
    return kind(**values)


def _value(value: Any, hint: Any) -> Any:
    while hasattr(hint, "__supertype__"):  # NewType, например PlayerID
        hint = hint.__supertype__
    origin, args = typing.get_origin(hint), typing.get_args(hint)
    if origin in (typing.Union, types.UnionType):
        if value is None and type(None) in args:
            return None
        (inner,) = [a for a in args if a is not type(None)]
        return _value(value, inner)
    if hint is int:
        if type(value) is not int:
            raise BadRequest("not_int")
        return value
    if hint is str:
        if not isinstance(value, str):
            raise BadRequest("not_str")
        return value
    if isinstance(hint, type) and issubclass(hint, Enum):
        return _enum(value, hint)
    if origin in (tuple, frozenset):
        if not isinstance(value, list):
            raise BadRequest("not_list")
        if origin is frozenset:
            return frozenset(_value(v, args[0]) for v in value)
        if len(args) == 2 and args[1] is Ellipsis:
            return tuple(_value(v, args[0]) for v in value)
        if len(value) != len(args):
            raise BadRequest("wrong_length")
        return tuple(_value(v, a) for v, a in zip(value, args, strict=True))
    if dataclasses.is_dataclass(hint):
        return _object(hint, value)
    raise BadRequest("unsupported")


def _enum[E: Enum](value: Any, kind: type[E]) -> E:
    for member in kind:
        name = (
            member.value if isinstance(member.value, str) else member.name
        ).lower()
        if value == name:
            return member
    raise BadRequest("bad_enum")
