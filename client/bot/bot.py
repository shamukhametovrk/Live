"""Бот для Live: обычный клиент без экрана.

Подключается к движку по WebSocket, садится за стол и играет случайно.
Говорит с движком только JSON — код движка не импортирует.

    uv run bot.py                       # один бот к localhost:8000
    uv run bot.py --count 2             # двое
    uv run bot.py --count 3 --start 3   # первый бот — хост, начнёт игру
"""

import argparse
import asyncio
import json
import random

import websockets

# Какие поля нужны предметам при применении (см. справочник движка).
ITEM_FIELDS = {
    "one-eye": ("chamber",),
    "reverse": ("chamber",),
    "peek": ("chamber",),
    "try-this": ("player", "chamber"),
    "play-along": ("player", "target"),
    "share": ("player", "take"),
}
HAND_LIMIT = 8


def decide(
    view: dict | None, me: int, rng: random.Random, start_at: int | None
):
    """Команда по снимку или None, если сейчас делать нечего."""
    if view is None:
        return None
    if view["type"] == "lobby":
        if start_at and view["host"] == me and len(view["players"]) >= start_at:
            return {"type": "start"}
        return None
    if view["type"] != "game_view" or view["round"] is None:
        return None
    round_ = view["round"]
    seats = {int(p): s for p, s in round_["seats"].items()}
    seat = seats.get(me)
    spread = round_["spread"]
    if seat is None or seat["health"] <= 0 or spread is None:
        return None
    alive = [p for p in round_["circle"] if seats[p]["health"] > 0]
    if spread["type"] == "preparing_view":
        if me in spread["decided"]:
            return None
        pool = seat["hand"] + spread["offer"]
        rng.shuffle(pool)
        chips = [0] * spread["size"]
        for _ in range(seat["chips"]):
            chips[rng.randrange(spread["size"])] += 1
        return {"type": "prepare", "hand": pool[:HAND_LIMIT], "chips": chips}
    if round_["active"] != me:
        return None
    free = [i for i, c in enumerate(spread["chambers"]) if not c["used"]]
    if not free:
        return None
    if seat["hand"] and rng.random() < 0.3:
        item = rng.choice(seat["hand"])
        cmd = {"type": "use_item", "item": item}
        others = [p for p in alive if p != me] or alive
        choices = {
            "chamber": free,
            "player": others if item == "share" else alive,
            "target": alive,
            "take": ["item", "chip"],
        }
        for field in ITEM_FIELDS.get(item, ()):
            cmd[field] = rng.choice(choices[field])
        return cmd
    chamber, target = rng.choice(free), rng.choice(alive)
    for effect in seat["effects"]:
        if effect["turn"] >= round_["turn"]:
            continue  # принуждение на себя — со следующего хода
        if effect["type"] == "play_along":
            target = effect["target"]
        if effect["type"] == "try_this":
            chamber = effect["chamber"]
    return {"type": "shoot", "chamber": chamber, "target": target}


async def play(
    url: str, rng: random.Random, start_at: int | None = None, delay: float = 0
) -> dict:
    """Играет одну партию; возвращает итоговый снимок."""
    async with websockets.connect(url) as ws:
        me = None
        waiting = dirty = False

        async def ask_snapshot() -> None:
            nonlocal waiting, dirty
            waiting, dirty = True, False
            await ws.send(json.dumps({"type": "snapshot"}))

        await ws.send(json.dumps({"type": "join"}))
        async for raw in ws:
            data = json.loads(raw)
            match data["type"]:
                case "welcome":
                    me = data["client"]
                case "message" | "rejected":
                    if data.get("code") == "paused":
                        await asyncio.sleep(0.2)
                    dirty = True
                    if not waiting:
                        await ask_snapshot()
                case "snapshot":
                    waiting = False
                    view = data["view"]
                    if view and view["type"] == "finished":
                        return view
                    if dirty:
                        await ask_snapshot()
                        continue
                    cmd = decide(view, me, rng, start_at)
                    if cmd:
                        await asyncio.sleep(delay)
                        await ws.send(json.dumps(cmd))
    raise ConnectionError("connection closed before the game finished")


async def main_async(args: argparse.Namespace) -> None:
    rng = random.Random(args.seed)
    bots = [
        play(
            args.url,
            random.Random(rng.random()),
            args.start if i == 0 else None,
            args.delay,
        )
        for i in range(args.count)
    ]
    results = await asyncio.gather(*bots)
    final = results[0]
    print(
        "Игра окончена. Победы по раундам:",
        [r["winner"] for r in final["results"]],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Бот для Live")
    parser.add_argument("--url", default="ws://localhost:8000/ws")
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument(
        "--start", type=int, help="первый бот начнёт игру, когда сядут N"
    )
    parser.add_argument("--delay", type=float, default=0.6)
    parser.add_argument("--seed", type=int)
    asyncio.run(main_async(parser.parse_args()))


if __name__ == "__main__":
    main()
