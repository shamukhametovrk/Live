[← Доменный слой](README.md)

# Модель данных

Всё состояние игры — неизменяемые классы (frozen dataclass). Правило не
меняет состояние, а возвращает новое (см. [правила](rules.md)).

## Диаграмма

```mermaid
classDiagram
direction TB
class Game { <<union>> }
class Lobby {
  host: PlayerID
  players: tuple~PlayerID~
  presence: frozendict~PlayerID, Presence~
  settings: Settings
}
class InProgress {
  settings: Settings
  players: tuple~PlayerID~
  presence: frozendict~PlayerID, Presence~
  results: tuple~RoundResult~
  round: Round
}
class Finished {
  players: tuple~PlayerID~
  presence: frozendict~PlayerID, Presence~
  results: tuple~RoundResult~
}
class Settings {
  rounds: int
  health: tuple~int, int~
  chambers: tuple~int, int~
  cartridges: tuple~int, int~
  excluded: frozenset~Item~
}
class RoundResult {
  first: PlayerID
  winner: PlayerID
}
class Round {
  start_health: int
  circle: tuple~PlayerID~
  first: PlayerID
  active: PlayerID
  turn: int
  seats: frozendict~PlayerID, Seat~
  spread: Spread
}
class Seat {
  health: int
  hand: tuple~Item~
  chips: int
  effects: tuple~Effect~
}
class Effect { <<union>> }
class Double { turn: int }
class FullForce { turn: int }
class Shield { turn: int }
class PlayAlong {
  turn: int
  target: PlayerID
}
class TryThis {
  turn: int
  chamber: int
}
class Spread { <<union>> }
class Preparing {
  size: int
  offers: frozendict~PlayerID, tuple~Item~~
  choices: frozendict~PlayerID, Choice~
}
class Choice {
  hand: tuple~Item~
  chips: tuple~int~
}
class Shooting {
  chambers: tuple~Chamber~
  chips: frozendict~PlayerID, tuple~int~~
  announced: int
  revealed: frozendict~PlayerID, frozenset~int~~
}
class Chamber {
  loaded: bool
  used: bool
}
Game <|-- Lobby
Game <|-- InProgress
Game <|-- Finished
Lobby *-- Settings
InProgress *-- Settings
InProgress *-- RoundResult
Finished *-- RoundResult
InProgress *-- Round
Round *-- Seat
Round *-- Spread
Seat *-- Effect
Effect <|-- Double
Effect <|-- FullForce
Effect <|-- Shield
Effect <|-- PlayAlong
Effect <|-- TryThis
Spread <|-- Preparing
Spread <|-- Shooting
Preparing *-- Choice
Shooting *-- Chamber
```

Стрелка с треугольником — «один из вариантов типа», а не наследование:
`Game = Lobby | InProgress | Finished`, `Spread = Preparing | Shooting`,
`Effect = Double | FullForce | Shield | PlayAlong | TryThis`.

## Игра

| Тип | Когда | Заметки |
| --- | --- | --- |
| `Lobby` | до начала | появляется на первом Join, поэтому хост есть всегда |
| `InProgress` | идёт раунд | |
| `Finished` | игра окончена | команд нет |

- `presence` — `PRESENT` / `AWAY` / `WITHDRAWN`. Пока кто-то `AWAY`, игра
  на паузе (см. [игру](../../../rules/chapters/game.md#потеря-связи)).
- `results` — итог каждого сыгранного раунда: кто начинал и кто выиграл.
- `Settings` — настройки хоста (см. [параметры](../../../rules/parameters.md)).
  Лимит руки — константа, не настройка.

## Раунд

- `start_health` — жизни в начале раунда; потолок для лечащих предметов.
- `circle` — круг, перетасован в начале раунда.
- `first` — первый ходящий; попадает в `RoundResult`.
- `active`, `turn` — чей ход и его номер в раунде. Номер растёт при
  каждой передаче хода и не меняется, когда ряд кончился посреди хода.
- `seats` — место каждого участника раунда.

## Место

- `health` — жизни. Выбывание ставит `0`.
- `hand` — рука.
- `chips` — заработанные фишки, ещё не положенные на каморы.
- `effects` — эффекты, не больше одного каждого вида. `turn` эффекта —
  номер хода, в который он появился; по нему считается срок (см.
  [эффекты](rules.md#эффекты)).

## Ряд

- `Preparing` — начало ряда. `size` — число камор, `offers` — что выпало
  каждому живому, `choices` — решения тех, кто уже решил.
- `Shooting` — ряд заряжен. `chips` — фишки каждого игрока по каморам,
  `announced` — сколько патронов объявлено, `revealed` — каморы, вес
  которых узнал каждый игрок.

## Что не хранится, а вычисляется

| Что | Как |
| --- | --- |
| Живой | `seat.health > 0` |
| Вес каморы | `1 + сумма фишек всех игроков на ней` |
| Счёт побед, сыграно раундов | по `results` |
| Сколько раз игрок начинал раунд | по `results` и текущему `first` |
| Победитель игры | невыбывший с наибольшим числом побед |
