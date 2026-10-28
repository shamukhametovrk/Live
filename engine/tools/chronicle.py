"""Летопись игры: боты играют партию, а она печатается словами правил.

Видно всё, включая скрытое: что легло в каморы, чьи фишки где, веса.
Каморы нумеруются с единицы, как в правилах.

    uv run python -m tools.chronicle                # случайная партия
    uv run python -m tools.chronicle --seed 7 --players 3 --rounds 2
    uv run python -m tools.chronicle --network      # с обрывами связи
"""

import argparse
import sys
from random import Random

from engine.core.domain import events as e
from engine.core.domain.catalog import Item
from engine.core.domain.commands import ChangeSettings
from engine.core.domain.errors import IllegalAction
from engine.core.domain.rules.handle import handle
from engine.core.domain.state import (
    Double,
    Effect,
    Finished,
    FullForce,
    Game,
    InProgress,
    Lobby,
    PlayAlong,
    Settings,
    Shield,
    Shooting,
    TryThis,
)
from tools.bot import game_command, lobby_command, presence_command

ITEM = {
    Item.ONE_EYE: "Одним глазом",
    Item.WIDE_EYES: "Во все глаза",
    Item.REVERSE: "Реверс",
    Item.MORE: "Хочу ещё",
    Item.SCARED: "Мне страшно",
    Item.PEEK: "Что тут у нас",
    Item.SHAKE: "ХАХхаахХАх",
    Item.WATER: "Глоток воды",
    Item.DUBIOUS: "Сомнительное удовольствие",
    Item.LIKE_NEW: "Как новый",
    Item.PASS: "Пасс",
    Item.DOUBLE: "Дубль",
    Item.FULL_FORCE: "Со всей дури",
    Item.SHIELD: "Настроечный щит",
    Item.TRY_THIS: "Попробуй вот эту",
    Item.PLAY_ALONG: "Подыграй мне",
    Item.SHARE: "Пора делиться",
    Item.JACKPOT: "Джекпот",
}


def items(hand) -> str:
    return ", ".join(f"«{ITEM[i]}»" for i in hand) or "ничего"


def effect(eff: Effect) -> str:
    match eff:
        case Double():
            return "«Дубль»"
        case FullForce():
            return "«Со всей дури»"
        case Shield():
            return "«Щит»"
        case PlayAlong(target=t):
            return f"«Подыграй мне»: стрелять в {t}"
        case TryThis(chamber=c):
            return f"«Попробуй вот эту»: камора {c + 1}"


def row(game: Game | None) -> str:
    if not isinstance(game, InProgress):
        return ""
    spread = game.round.spread
    if not isinstance(spread, Shooting):
        return ""
    marks = []
    for c in spread.chambers:
        mark = "●" if c.loaded else "○"
        marks.append(f"[{mark}]" if c.used else f" {mark} ")
    weights = " ".join(f"{w:>3}" for w in spread.weights)
    return f"      ряд   {''.join(marks)}\n      веса  {weights}"


def describe(ev: e.Event, game: Game | None) -> list[str]:
    """Строки летописи для события; `game` — состояние после команды."""
    rnd = game.round if isinstance(game, InProgress) else None

    def hp(p) -> str:
        return f"{rnd.seats[p].health}" if rnd else "?"

    match ev:
        case e.Joined(p):
            return [f"Игрок {p} сел за стол."]
        case e.Left(p):
            return [f"Игрок {p} ушёл из-за стола."]
        case e.Cancelled():
            return ["Хост ушёл — игры не будет."]
        case e.SettingsChanged(s):
            ex = items(sorted(s.excluded, key=lambda i: i.value))
            return [
                f"Настройки: раундов {s.rounds}, жизни {s.health[0]}–"
                f"{s.health[1]}, каморы {s.chambers[0]}–{s.chambers[1]}, "
                f"патроны {s.cartridges[0]}–{s.cartridges[1]}, "
                f"исключены: {ex}."
            ]
        case e.Disconnected(p):
            return [f"!! Игрок {p} потерял связь — пауза."]
        case e.Reconnected(p):
            return [f"!! Игрок {p} вернулся."]
        case e.Withdrew(p):
            return [f"!! Игрок {p} не вернулся вовремя и выбыл."]
        case e.GameStarted(players):
            return [f"Игра началась: игроки {', '.join(map(str, players))}."]
        case e.RoundStarted(health, circle, first):
            order = " → ".join(map(str, circle))
            return [
                "",
                f"══════ Раунд. Жизней у всех: {health}. Круг: {order}. "
                f"Первым ходит {first}.",
            ]
        case e.SpreadStarted(size, offers):
            lines = ["", f"── Ряд: {size} камор. Выдача:"]
            lines += [f"     {p}: {items(o)}" for p, o in offers.items()]
            return lines
        case e.Prepared():
            return []
        case e.Loaded(_, hands, chips, loaded, announced):
            lines = ["   Все решили. Руки:"]
            lines += [f"     {p}: {items(h)}" for p, h in hands.items()]
            placed = {p: c for p, c in chips.items() if any(c)}
            for p, c in placed.items():
                lines.append(f"   Фишки {p} по каморам: {list(c)}")
            lines.append(
                f"   Зарядка: {''.join('●' if x else '○' for x in loaded)}"
                f" — объявлено патронов: {announced}"
            )
            return lines
        case e.SpreadEnded():
            return ["   Каморы кончились."]
        case e.Shot(shooter, chamber, target, loaded, damage):
            who = "себя" if target == shooter else f"игрока {target}"
            if not loaded:
                result = "холостой"
            elif damage == 0:
                result = "патрон, но «Щит» погасил попадание"
            else:
                result = f"патрон, −{damage} (жизней у {target}: {hp(target)})"
            return [
                f"   {shooter} стреляет в {who} каморой {chamber + 1}: {result}"
            ]
        case e.ChipEarned(p):
            return [f"      +1 фишка игроку {p}"]
        case e.Died(p):
            return [f"      ✝ игрок {p} погиб"]
        case e.TurnPassed(active, turn):
            return [f"── ход {turn}: игрок {active}"]
        case e.EffectAdded(owner, eff):
            actor = rnd.active if rnd else "?"
            whom = "" if owner == actor else f" на игрока {owner}"
            return [f"   {actor}: {effect(eff)}{whom}"]
        case e.EffectRemoved(owner, eff):
            return [f"      с игрока {owner} снят {effect(eff)}"]
        case e.WeightSeen(actor, chamber, weight):
            return [
                f"   {actor}: «Одним глазом» на камору {chamber + 1} — вес "
                f"{weight} (видит только он)"
            ]
        case e.WeightsSeen(actor, weights):
            return [f"   {actor}: «Во все глаза» — веса {list(weights)}"]
        case e.Reversed(actor, chamber, now):
            state = "патрон" if now else "пусто"
            return [
                f"   {actor}: «Реверс» камору {chamber + 1} — теперь там "
                f"{state} (не знает никто)"
            ]
        case e.CartridgeAdded(actor, chamber):
            return [
                f"   {actor}: «Хочу ещё» — патрон лёг в камору {chamber + 1} "
                "(скрыто)"
            ]
        case e.CartridgeRemoved(actor, chamber):
            return [
                f"   {actor}: «Мне страшно» — патрон снят с каморы "
                f"{chamber + 1} (скрыто)"
            ]
        case e.Peeked(actor, chamber, loaded):
            state = "патрон" if loaded else "пусто"
            return [
                f"   {actor}: «Что тут у нас» камора {chamber + 1} — {state}"
            ]
        case e.Shaken(actor, _):
            return [f"   {actor}: «ХАХхаахХАх» — патроны перемешаны"]
        case e.Healed(actor, item, amount):
            return [
                f"   {actor}: «{ITEM[item]}» +{amount} (жизней: {hp(actor)})"
            ]
        case e.Gambled(actor, won, amount):
            how = "повезло" if won else "не повезло"
            return [
                f"   {actor}: «Сомнительное удовольствие» — {how}, "
                f"{amount:+} (жизней: {hp(actor)})"
            ]
        case e.Passed(actor):
            return [f"   {actor}: «Пасс»"]
        case e.ItemStolen(actor, victim, item):
            return [
                f"   {actor}: «Пора делиться» — забрал у {victim} "
                f"«{ITEM[item]}»"
            ]
        case e.ChipStolen(actor, victim):
            return [f"   {actor}: «Пора делиться» — забрал у {victim} фишку"]
        case e.Jackpot(actor):
            return [f"   {actor}: «Джекпот» — +3 фишки"]
        case e.Wasted(actor, item):
            return [f"   {actor}: «{ITEM[item]}» — впустую"]
        case e.RoundEnded(winner):
            return [f"══════ Раунд выиграл игрок {winner}."]
        case e.GameFinished(winners):
            names = ", ".join(map(str, winners)) or "никто"
            return ["", f"Игра окончена. Победа: {names}."]
    return [repr(ev)]


SHOW_ROW = (
    e.Loaded,
    e.Shot,
    e.Peeked,
    e.Reversed,
    e.CartridgeAdded,
    e.CartridgeRemoved,
    e.Shaken,
)


def chronicle(
    seed: int, players: int | None, rounds: int | None, network: bool
) -> None:
    rng = Random(seed)
    seats = players or rng.randint(2, 6)
    print(f"Партия seed={seed}, игроков {seats}.")
    game: Game | None = None
    for _ in range(20000):
        if isinstance(game, Finished):
            return
        if network and game is not None and rng.random() < 0.02:
            actor, cmd = presence_command(game, rng)
        elif game is None or isinstance(game, Lobby):
            actor, cmd = lobby_command(game, seats, rng)
            if rounds and isinstance(cmd, ChangeSettings):
                cmd = ChangeSettings(Settings(rounds=rounds))
        else:
            actor, cmd = game_command(game, rng)
        try:
            outcome = handle(game, actor, cmd, rng)
        except IllegalAction:
            continue
        game = outcome.game
        for ev in outcome.events:
            for line in describe(ev, game):
                print(line)
            if isinstance(ev, SHOW_ROW) and (text := row(game)):
                print(text)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--players", type=int, choices=range(2, 7))
    parser.add_argument("--rounds", type=int, choices=range(1, 8))
    parser.add_argument("--network", action="store_true")
    args = parser.parse_args()
    seed = args.seed if args.seed is not None else Random().randrange(10**6)
    sys.stdout.reconfigure(encoding="utf-8")
    chronicle(seed, args.players, args.rounds, args.network)


if __name__ == "__main__":
    main()
