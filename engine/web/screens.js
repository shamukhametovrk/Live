// Экраны: отрисовка по снимку и ввод игрока (см. «Дизайн» в docs/engine/web-client.md).

const ui = {
  view: null,
  chamber: null,    // выбранная камора
  pending: null,    // предмет, которому собираем поля: {item, fields, cmd}
  prep: null,       // начало ряда: {key, keep: [bool], chips: [int]}
  announced: null,  // число патронов, пока оно горит: {n, at}
};

const $ = (id) => document.getElementById(id);

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "onclick") node.onclick = v;
    else if (k === "class") node.className = v;
    else if (k === "style") node.style.cssText = v;
    else if (v !== false && v !== null && v !== undefined) node.setAttribute(k, v);
  }
  for (const child of children.flat()) {
    if (child !== null && child !== undefined && child !== false) {
      node.append(child instanceof Node ? child : String(child));
    }
  }
  return node;
}

function render(view) {
  ui.view = view;
  const table = $("table");
  table.hidden = false;
  table.replaceChildren(screenFor(view), layer);
  const away = view && view.presence
    ? Object.entries(view.presence).filter(([, s]) => s === "away").map(([p]) => p)
    : [];
  $("pause").hidden = away.length === 0;
  $("pause").textContent = `Пауза: без связи ${away.join(", ")}. Ждём…`;
}

function screenFor(view) {
  if (view === null) {
    return Net.me === null
      ? el("div", { class: "screen-card" }, el("p", {}, "Стол пуст или игра уже идёт."), sitButton())
      : el("p", { class: "dim" }, "Ждём…");
  }
  switch (view.type) {
    case "lobby": return lobby(view);
    case "game_view": return game(view);
    case "finished": return finished(view);
    default: return el("p", {}, view.type);
  }
}

function sitButton() {
  return el("button", { onclick: () => Net.send({ type: "join" }) }, "Сесть за стол");
}

// Лобби

function lobby(view) {
  const me = Net.me;
  const seated = view.players.includes(me);
  const list = view.players.map((p) =>
    el("li", {}, `игрок ${p}`, p === view.host ? " (хост)" : "",
      p === me ? " — вы" : "", view.presence[p] === "away" ? " [нет связи]" : ""));
  const parts = [el("p", {}, "Лобби. За столом:"), el("ul", {}, list)];
  if (!seated) parts.push(sitButton());
  if (seated && me === view.host) {
    const rounds = el("input", { type: "number", min: 1, max: 7, value: view.settings.rounds });
    parts.push(el("div", { class: "actions" },
      "Раундов: ", rounds,
      el("button", {
        onclick: () => Net.send({
          type: "change_settings",
          settings: { rounds: Number(rounds.value) },
        }),
      }, "Сохранить"),
      el("button", { onclick: () => Net.send({ type: "start" }) }, "Начать")));
  } else if (seated) {
    parts.push(el("p", { class: "dim" }, "Ждём, пока хост начнёт."));
  }
  if (seated) {
    parts.push(el("div", { class: "actions" },
      el("button", { onclick: () => Net.send({ type: "leave" }) }, "Уйти")));
  }
  return el("div", { class: "screen-card" }, parts);
}

// Стол

// Где сидит игрок: доля от размера стола. Вы — внизу, дальше по кругу хода.
function seatSpot(round, player, radius) {
  const circle = round.circle;
  const me = circle.includes(Net.me) ? Net.me : circle[0];
  const i = (circle.indexOf(player) - circle.indexOf(me) + circle.length) % circle.length;
  const angle = Math.PI / 2 + (2 * Math.PI * i) / circle.length;
  return { x: 50 + radius * Math.cos(angle), y: 50 + radius * Math.sin(angle) };
}

function at(spot) {
  return `left:${spot.x}%;top:${spot.y}%`;
}

function game(view) {
  const round = view.round;
  if (!round || !round.spread) return el("p", { class: "dim" }, "…");
  const spread = round.spread;
  const seat = round.seats[Net.me];
  const parts = [
    el("div", { class: "felt" }),
    el("div", { class: "round-mark" },
      `раунд ${view.results.length + 1}/${view.settings.rounds}`),
    row(round, spread),
    ...round.circle.filter((p) => p !== Net.me).map((p) => otherHand(round, p)),
    ...round.circle.map((p) => player(round, p)),
  ];
  if (ui.pending) parts.push(pendingPanel());
  const board = el("div", { class: "board" }, parts);
  const screen = [board];
  if (seat) screen.push(myHand(round, seat));
  if (spread.type === "preparing_view") {
    screen.push(preparing(round, spread));
  }
  return el("div", { class: "game" }, screen);
}

function row(round, spread) {
  const shooting = spread.type === "shooting_view";
  const mine = shooting && round.active === Net.me;
  const chambers = shooting
    ? spread.chambers
    : Array.from({ length: spread.size }, () => ({ used: false, loaded: null }));
  const cells = chambers.map((c, i) => {
    const cls = ["chamber",
      c.used ? (c.loaded ? "loaded" : "blank") : "",
      ui.chamber === i ? "picked" : "",
      mine && !c.used ? "live" : ""].join(" ");
    const weight = shooting && spread.seen[i] !== undefined
      ? el("span", { class: "weight" }, spread.seen[i]) : null;
    const chips = shooting && spread.chips && spread.chips[i]
      ? el("span", { class: "chips-on" }, chipStack(spread.chips[i])) : null;
    return el("div", {
      class: cls,
      onclick: shooting && !c.used ? () => pickChamber(i) : null,
    }, el("span", { class: "core" }), weight, chips);
  });
  // Перерисовка не должна перезапускать вспышку: продолжаем с того же места.
  const announced = ui.announced !== null
    ? el("div", {
      class: "announced",
      style: `animation-delay:-${Date.now() - ui.announced.at}ms`,
    }, ui.announced.n) : null;
  return el("div", { class: "row" }, cells, announced);
}

function player(round, p) {
  const s = round.seats[p];
  const alive = s.health > 0;
  const field = ui.pending && ui.pending.fields[0];
  const aiming = (round.active === Net.me && ui.chamber !== null && !ui.pending)
    || field === "player" || field === "target";
  const cls = ["seat",
    p === round.active ? "active" : "",
    p === Net.me ? "me" : "",
    alive ? "" : "dead",
    aiming && alive ? "aim" : ""].join(" ");
  const lives = Array.from({ length: Math.max(round.start_health, s.health) },
    (_, i) => el("span", { class: i < s.health ? "life" : "life lost" }));
  return el("div", {
    class: cls,
    style: at(seatSpot(round, p, 44)),
    "data-player": p,
    onclick: alive ? () => pickPlayer(p) : null,
  },
  el("div", { class: "plate" }, p === Net.me ? "вы" : p),
  el("div", { class: "lives" }, lives),
  s.chips ? el("div", { class: "chips" }, chipStack(s.chips)) : null,
  s.effects.length
    ? el("div", { class: "effects" }, s.effects.map((e) =>
      el("span", { class: "effect", title: effectText(e) }, icon(EFFECT_ITEM[e.type]))))
    : null);
}

function otherHand(round, p) {
  const hand = round.seats[p].hand;
  if (!hand.length) return null;
  const spot = seatSpot(round, p, 30);
  // Сбоку рука легла бы на ряд камор — сдвигаем её ниже ряда.
  if (Math.abs(spot.y - 50) < 12) spot.y = 63;
  return el("div", { class: "hand-small", style: at(spot) },
    hand.map((item) => itemTile(item)));
}

function myHand(round, seat) {
  const mine = round.active === Net.me && round.spread.type === "shooting_view";
  const tiles = seat.hand.map((item) => itemTile(item, mine ? () => useItem(item) : null,
    ui.pending && ui.pending.item === item));
  return el("div", { class: "my-hand" },
    tiles.length ? tiles : el("span", { class: "dim" }, "рука пуста"));
}

function itemTile(item, onclick, active) {
  return el("span", {
    class: `item ${ITEM_CLASS[item] || ""}${onclick ? " usable" : ""}${active ? " active" : ""}`,
    title: ITEMS[item] || item,
    onclick,
  }, icon(item));
}

// Значок — маска: рисуется цветом текста (см. icons/README.md).
function icon(item) {
  return el("span", { class: "icon", style: `--icon:url("icons/${item}.svg")` });
}

function chipStack(n) {
  return Array.from({ length: n }, () => el("span", { class: "chip" }));
}

// Ввод

function pickChamber(i) {
  if (ui.pending && ui.pending.fields[0] === "chamber") return fill("chamber", i);
  if (ui.view.round.active !== Net.me) return;
  ui.chamber = ui.chamber === i ? null : i;
  render(ui.view);
}

function pickPlayer(p) {
  const field = ui.pending && ui.pending.fields[0];
  if (field === "player" || field === "target") return fill(field, p);
  const round = ui.view.round;
  if (ui.pending || ui.chamber === null || round.active !== Net.me) return;
  Net.send({ type: "shoot", chamber: ui.chamber, target: p });
  ui.chamber = null;
}

function useItem(item) {
  if (ui.pending && ui.pending.item === item) {
    ui.pending = null;
    return render(ui.view);
  }
  const fields = ITEM_FIELDS[item] || [];
  ui.pending = { item, fields: [...fields], cmd: { type: "use_item", item } };
  if (fields.length === 0) return sendPending();
  render(ui.view);
}

function fill(field, value) {
  ui.pending.cmd[field] = value;
  ui.pending.fields.shift();
  if (ui.pending.fields.length === 0) return sendPending();
  render(ui.view);
}

function sendPending() {
  Net.send(ui.pending.cmd);
  ui.pending = null;
  render(ui.view);
}

function pendingPanel() {
  const asks = {
    chamber: "камора?",
    player: "игрок?",
    target: "цель?",
    take: "что забрать?",
  };
  const field = ui.pending.fields[0];
  return el("div", { class: "pending" },
    el("div", {}, icon(ui.pending.item), ` ${asks[field]}`),
    field === "take" ? el("div", { class: "actions" },
      el("button", { onclick: () => fill("take", "item") }, "предмет"),
      el("button", { onclick: () => fill("take", "chip") }, "фишку")) : null);
}

// Начало ряда — окно поверх стола

function preparing(round, spread) {
  const me = Net.me;
  const seat = round.seats[me];
  const waiting = round.circle.filter((p) => round.seats[p].health > 0 && !spread.decided.includes(p));
  if (!seat || seat.health <= 0 || spread.decided.includes(me)) {
    return el("div", { class: "modal quiet" }, `ждём: ${waiting.join(", ")}`);
  }
  const pool = [...seat.hand, ...spread.offer];
  const key = JSON.stringify([round.turn, spread.size, pool]);
  if (!ui.prep || ui.prep.key !== key) {
    ui.prep = { key, keep: pool.map((_, i) => i < 8), chips: Array(spread.size).fill(0) };
  }
  const prep = ui.prep;
  const kept = prep.keep.filter(Boolean).length;
  const items = pool.map((item, i) => el("button", {
    class: `pick ${prep.keep[i] ? "on" : ""}`,
    title: ITEMS[item],
    onclick: () => { prep.keep[i] = !prep.keep[i]; render(ui.view); },
  }, icon(item), el("span", {}, ITEMS[item]), i >= seat.hand.length ? " ★" : ""));
  const left = seat.chips - prep.chips.reduce((a, b) => a + b, 0);
  const chambers = prep.chips.map((n, i) => el("div", { class: "prep-chamber" },
    el("span", {}, i + 1),
    el("span", { class: "chips" }, chipStack(n)),
    el("button", { disabled: left <= 0, onclick: () => { prep.chips[i]++; render(ui.view); } }, "+"),
    el("button", { disabled: n <= 0, onclick: () => { prep.chips[i]--; render(ui.view); } }, "−")));
  return el("div", { class: "modal" },
    el("p", {}, `Рука: ${kept} из 8`), el("div", { class: "hand" }, items),
    seat.chips ? el("p", {}, "Фишки на каморы: ", chipStack(left)) : null,
    seat.chips ? el("div", { class: "prep-row" }, chambers) : null,
    el("div", { class: "actions" }, el("button", {
      disabled: kept > 8 || left !== 0,
      onclick: () => Net.send({
        type: "prepare",
        hand: pool.filter((_, i) => prep.keep[i]),
        chips: prep.chips,
      }),
    }, "Готово")));
}

// Подписи: сообщения движка всплывают у игрока, к которому относятся

const QUIET = new Set(["prepared", "turn_passed", "effect_removed", "joined",
  "left", "settings_changed", "reconnected", "game_started", "spread_started"]);

function onMessage(m) {
  if (m.type === "loaded") {
    ui.announced = { n: m.announced, at: Date.now() };
    setTimeout(() => { ui.announced = null; if (ui.view) render(ui.view); }, 2500);
    return;
  }
  if (QUIET.has(m.type)) return;
  bubble(caption(m), m.type === "shot" && m.loaded && m.damage ? "hit" : "",
    m.target ?? m.player ?? m.owner ?? m.actor ?? m.shooter ?? null);
}

// Подпись: значок предмета и короткий итог; без предмета — слово.
function caption(m) {
  const sign = (n) => (n >= 0 ? `+${n}` : `${n}`);
  switch (m.type) {
    case "shot": return !m.loaded ? "щёлк" : m.damage === 0 ? "щит" : `−${m.damage}`;
    case "died": return "✝";
    case "chip_earned": return "+◆";
    case "effect_added": return [icon(EFFECT_ITEM[m.effect.type])];
    case "weight_seen": return [icon("one-eye"), m.weight === null ? "" : ` ${m.weight}`];
    case "weights_seen": return [icon("wide-eyes"), m.weights === null ? "" : ` ${m.weights.join(" ")}`];
    case "reversed": return [icon("reverse")];
    case "cartridge_added": return [icon("more"), " +1"];
    case "cartridge_removed": return [icon("scared"), " −1"];
    case "peeked": return [icon("peek"), m.loaded ? " патрон" : " пусто"];
    case "shaken": return [icon("shake")];
    case "healed": return [icon(m.item), ` +${m.amount}`];
    case "gambled": return [icon("dubious"), ` ${sign(m.amount)}`];
    case "passed": return [icon("pass")];
    case "item_stolen": return [icon("share"), " ", icon(m.item)];
    case "chip_stolen": return [icon("share"), " ◆"];
    case "jackpot": return [icon("jackpot"), " +3◆"];
    case "wasted": return [icon(m.item), " впустую"];
    default: return describe(m);
  }
}

function onRejected(code) {
  bubble(REJECTIONS[code] || code, "bad", null);
}

// Слой подписей живёт поверх стола и переживает перерисовку.
const layer = el("div", { class: "bubbles" });

function bubble(text, kind, playerId) {
  const table = $("table");
  const seat = playerId === null ? null
    : table.querySelector(`.seat[data-player="${playerId}"]`);
  const box = table.getBoundingClientRect();
  let x = box.width / 2, y = Math.min(box.width, box.height) * 0.38;
  if (seat) {
    const r = seat.getBoundingClientRect();
    x = r.left + r.width / 2 - box.left;
    y = r.top - box.top;
  }
  // Подписи у одного места встают столбиком, а не друг на друга.
  const key = String(playerId);
  const stacked = [...layer.children].filter((b) => b.dataset.key === key).length;
  const node = el("div", {
    class: `bubble ${kind}`,
    "data-key": key,
    style: `left:${x}px;top:${y - stacked * 30}px`,
  }, text);
  layer.append(node);
  setTimeout(() => node.remove(), 2600);
}

// Конец игры

function finished(view) {
  const wins = {};
  for (const r of view.results) wins[r.winner] = (wins[r.winner] || 0) + 1;
  const rows = view.players.map((p) => el("li", {},
    `игрок ${p}: побед ${wins[p] || 0}`,
    view.presence[p] === "withdrawn" ? " (выбыл)" : "",
    p === Net.me ? " — вы" : ""));
  return el("div", { class: "screen-card" },
    el("p", {}, "Игра окончена. Скоро стол опустеет."),
    el("ul", {}, rows),
    el("div", { class: "actions" },
      el("button", { onclick: () => Net.send({ type: "history" }) }, "История")));
}

// Запуск

Net.onSnapshot = render;
Net.onMessage = onMessage;
Net.onRejected = onRejected;

// Страницу отдаёт сам движок — подключаемся к тому же адресу.
Net.connect(location.host || "localhost:8000");

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && (ui.pending || ui.chamber !== null)) {
    ui.pending = null;
    ui.chamber = null;
    if (ui.view) render(ui.view);
  }
});
