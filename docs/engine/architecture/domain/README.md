# Доменный слой

Домен — это **модель данных** и **правила**, которые её меняют. Правила
игры, на которых он основан, — в [`docs/rules/`](../../../rules/index.md).

- [Модель данных](state.md) — что хранится: неизменяемое состояние игры.
- [Команды и события](commands.md) — что приходит в домен и что из него
  выходит; каталог предметов.
- [Правила](rules.md) — как оно меняется: функции, сгруппированные по
  стадиям игры.

Почему так — решения
[0012](../../decisions/0012-immutable-state-pure-rules.md),
[0013](../../decisions/0013-events-and-visibility-function.md),
[0015](../../decisions/0015-effects-are-data.md) и
[0016](../../decisions/0016-spread-start-is-one-step.md).

## Модули

```text
state.py       модель данных, включая эффекты
catalog.py     предметы: класс, какие параметры нужны
commands.py    команды
events.py      события
rules/
  handle.py    вход: пауза, кто действует, выбор правила по стадии
  lobby.py     join, leave, change_settings, start
  presence.py  disconnect, reconnect, timeout / withdraw
  prepare.py   начало ряда: start_spread, prepare, load
  shoot.py     выстрел
  apply.py     применение предмета: по ветке на предмет
  effects.py   add_effect, expired
  settle.py    последствия: гибель → конец раунда → конец хода → конец ряда
  round.py     start_round, finish
visibility.py  view, project
```

Прикладной слой вызывает только `handle` и функции видимости.
