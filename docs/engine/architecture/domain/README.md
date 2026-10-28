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
ids.py         идентификатор игрока
parameters.py  числа игры
catalog.py     справочник предметов: класс, поля применения, эффект
state.py       модель данных, включая эффекты
commands.py    команды
events.py      события
errors.py      IllegalAction
rules/
  handle.py    вход: стадия, пауза, кто действует → правило
  lobby.py     join, leave, change_settings, start
  presence.py  disconnect, reconnect, timeout
  round.py     start_round
  prepare.py   начало ряда: deal, prepare, load_if_ready
  shoot.py     выстрел
  apply.py     применение предмета: общие проверки и ветка на предмет
  chambers.py  использовать камору — общее для выстрела и предметов
  effects.py   find, in_force, expired
  settle.py    последствия: гибель → конец раунда и игры → конец хода → конец ряда
visibility.py  view, project (ещё не написано)
```

Прикладной слой вызывает только `handle` и функции видимости.
