// Экраны: отрисовка по снимку и ввод игрока. Интерфейс пока простой.

const ui = {
  view: null,
  chamber: null,    // выбранная камора
  target: null,     // выбранная цель
  pending: null,    // предмет, которому собираем поля: {item, fields, cmd}
  prep: null,       // начало ряда: {key, keep: [bool], chips: [int]}
};

const $ = (id) => document.getElementById(id);

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "onclick") node.onclick = v;
    else if (k === "class") node.className = v;
    else if (v !== false && v !== null && v !== undefined) node.setAttribute(k, v);
  }
  for (const child of children.flat()) {
    if (child !== null && child !== undefined && child !== false) {
      node.append(child instanceof Node ? child : String(child));
    }
  }
  return node;
}

function line(text, kind) {
  const feed = $("feed");
  const cls = kind === "rejected" ? "bad" : kind === "shot" ? "hot" : "";
  feed.append(el("p", { class: cls }, `> ${text}`));
  feed.scrollTop = feed.scrollHeight;
}

function render(view) {
  ui.view = view;
  const table = $("table");
  table.hidden = false;
  table.replaceChildren(screenFor(view));
  const away = view && view.presence
    ? Object.entries(view.presence).filter(([, s]) => s === "away").map(([p]) => p)
    : [];
  $("pause").hidden = away.length === 0;
  $("pause").textContent = `Пауза: без связи ${away.join(", ")}. Ждём…`;
}

function screenFor(view) {
  if (view === null) {
    return Net.me === null
      ? el("div", {}, el("p", {}, "Стол пуст или игра уже идёт."), sitButton())
      : el("p", {}, "Ждём…");
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
  return el("div", {}, parts);
}

// Игра

function game(view) {
  const round = view.round;
  if (!round || !round.spread) return el("p", {}, "…");
  const seats = round.seats;
  const header = el("p", { class: "dim" },
    `раунд ${view.results.length + 1} из ${view.settings.rounds} · ход ${round.turn}`,
    ` · ходит ${round.active === Net.me ? "ВЫ" : round.active}`);
  const body = round.spread.type === "preparing_view"
    ? preparing(round, round.spread)
    : shooting(round, round.spread);
  return el("div", {}, header, players(round), body);
}

function players(round) {
  return el("div", { class: "players" }, round.circle.map((p) => {
    const s = round.seats[p];
    const alive = s.health > 0;
    const cls = ["player", p === round.active ? "active" : "",
      p === ui.target ? "target" : "", alive ? "" : "dead"].join(" ");
    const name = p === Net.me ? `${p} (вы)` : `${p}`;
    const hp = alive ? "♥".repeat(s.health) : "✝";
    const effects = s.effects.map((e) => `[${effectText(e)}]`).join(" ");
    const hand = s.hand.length ? ` · ${s.hand.map((i) => ITEMS[i]).join(", ")}` : "";
    return el("div", { class: cls, onclick: alive ? () => pickPlayer(p) : null },
      `${name} ${hp} ◆${s.chips} ${effects}`, el("span", { class: "dim" }, hand));
  }));
}

// Начало ряда

function preparing(round, spread) {
  const me = Net.me;
  const seat = round.seats[me];
  const waiting = round.circle.filter((p) => round.seats[p].health > 0 && !spread.decided.includes(p));
  const note = el("p", { class: "dim" }, `ряд: ${spread.size} камор · ещё решают: ${waiting.join(", ") || "никто"}`);
  if (!seat || seat.health <= 0 || spread.decided.includes(me)) {
    return el("div", {}, note, el("p", {}, "Ждём остальных…"));
  }
  const pool = [...seat.hand, ...spread.offer];
  const key = JSON.stringify([round.turn, spread.size, pool]);
  if (!ui.prep || ui.prep.key !== key) {
    ui.prep = { key, keep: pool.map((_, i) => i < 8), chips: Array(spread.size).fill(0) };
  }
  const prep = ui.prep;
  const kept = prep.keep.filter(Boolean).length;
  const items = pool.map((item, i) => el("button", {
    class: prep.keep[i] ? "on" : "",
    onclick: () => { prep.keep[i] = !prep.keep[i]; render(ui.view); },
  }, ITEMS[item], i >= seat.hand.length ? " (новый)" : ""));
  const left = seat.chips - prep.chips.reduce((a, b) => a + b, 0);
  const chambers = prep.chips.map((n, i) => el("div", { class: "chamber" },
    `${i + 1}`, el("small", {}, `фишек ${n}`),
    el("button", { disabled: left <= 0, onclick: () => { prep.chips[i]++; render(ui.view); } }, "+"),
    el("button", { disabled: n <= 0, onclick: () => { prep.chips[i]--; render(ui.view); } }, "−")));
  return el("div", {}, note,
    el("p", {}, `Что оставить в руке (${kept} из 8):`), el("div", { class: "hand" }, items),
    seat.chips ? el("p", {}, `Фишки: осталось разложить ${left}`) : null,
    seat.chips ? el("div", { class: "row" }, chambers) : null,
    el("div", { class: "actions" }, el("button", {
      disabled: kept > 8 || left !== 0,
      onclick: () => Net.send({
        type: "prepare",
        hand: pool.filter((_, i) => prep.keep[i]),
        chips: prep.chips,
      }),
    }, "Готово")));
}

// Стрельба

function shooting(round, spread) {
  const mine = round.active === Net.me;
  const row = el("div", { class: "row" }, spread.chambers.map((c, i) => {
    const mark = c.used ? (c.loaded ? "●" : "○") : "?";
    const weight = spread.seen[i] !== undefined ? `вес ${spread.seen[i]}` : "";
    return el("button", {
      class: `chamber ${ui.chamber === i ? "picked" : ""}`,
      disabled: c.used,
      onclick: () => pickChamber(i),
    }, mark, el("small", {}, `${i + 1} ${weight}`));
  }));
  const seat = round.seats[Net.me];
  const hand = seat ? seat.hand.map((item) => el("button", {
    disabled: !mine,
    onclick: () => useItem(item),
  }, ITEMS[item])) : [];
  const actions = [];
  if (mine) {
    actions.push(el("button", {
      disabled: ui.chamber === null || ui.target === null,
      onclick: shoot,
    }, "Выстрел"));
  }
  if (ui.pending) {
    actions.push(el("span", { class: "hot" }, pendingHint()));
    if (ui.pending.fields[0] === "take") {
      actions.push(el("button", { onclick: () => fill("take", "item") }, "забрать предмет"));
      actions.push(el("button", { onclick: () => fill("take", "chip") }, "забрать фишку"));
    }
    actions.push(el("button", { onclick: () => { ui.pending = null; render(ui.view); } }, "отмена"));
  }
  return el("div", {}, row,
    el("p", { class: "row-note" }, `патронов объявлено: ${spread.announced}`,
      spread.chips && spread.chips.some(Boolean)
        ? ` · ваши фишки по каморам: ${spread.chips.join(" ")}` : ""),
    seat ? el("div", { class: "hand" }, "Рука: ", hand.length ? hand : el("span", { class: "dim" }, "пусто"),
      el("span", { class: "dim" }, ` · фишек ${seat.chips}`)) : null,
    el("div", { class: "actions" }, actions),
    mine && !ui.pending ? el("p", { class: "dim" }, "Выберите камору и цель (клик по игроку), затем «Выстрел».") : null);
}

function pickChamber(i) {
  if (ui.pending && ui.pending.fields[0] === "chamber") return fill("chamber", i);
  ui.chamber = i;
  render(ui.view);
}

function pickPlayer(p) {
  const field = ui.pending && ui.pending.fields[0];
  if (field === "player" || field === "target") return fill(field, p);
  ui.target = p;
  render(ui.view);
}

function useItem(item) {
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

function pendingHint() {
  const asks = {
    chamber: "выберите камору",
    player: "выберите игрока",
    target: "выберите цель",
    take: "что забрать?",
  };
  return `${ITEMS[ui.pending.item]}: ${asks[ui.pending.fields[0]]}`;
}

function shoot() {
  Net.send({ type: "shoot", chamber: ui.chamber, target: ui.target });
  ui.chamber = null;
}

// Конец игры

function finished(view) {
  const wins = {};
  for (const r of view.results) wins[r.winner] = (wins[r.winner] || 0) + 1;
  const rows = view.players.map((p) => el("li", {},
    `игрок ${p}: побед ${wins[p] || 0}`,
    view.presence[p] === "withdrawn" ? " (выбыл)" : "",
    p === Net.me ? " — вы" : ""));
  return el("div", {}, el("p", {}, "Игра окончена. Скоро стол опустеет."),
    el("ul", {}, rows),
    el("div", { class: "actions" },
      el("button", { onclick: () => Net.send({ type: "history" }) }, "История")));
}

// Запуск

Net.onSnapshot = render;
Net.onLine = line;

// Страницу отдаёт сам движок — подключаемся к тому же адресу.
Net.connect(location.host || "localhost:8000");

document.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && ui.view && ui.view.type === "game_view"
      && ui.chamber !== null && ui.target !== null && !ui.pending) {
    shoot();
  }
});
