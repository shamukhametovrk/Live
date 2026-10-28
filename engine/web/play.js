// Проигрывание: сообщения движка идут по очереди, каждое — анимацией на
// столе, который сейчас нарисован. Свежий снимок рисуется, когда очередь
// опустела: так выстрел успевает вскрыть камору, даже если ряд на нём
// закончился и снимок уже показывает следующий.

const Play = {
  queue: [],
  playing: false,
  latest: undefined,  // последний снимок, ещё не нарисованный
  received: 0,        // сколько сообщений пришло
  covered: 0,         // сколько из них учтено в последнем снимке
  waiters: [],

  busy() {
    return Play.playing || Play.queue.length > 0;
  },

  snapshot(view) {
    Play.latest = view;
    Play.covered = Play.received;
    for (const done of Play.waiters.splice(0)) done();
    if (!Play.busy()) Play.sync();
  },

  message(m) {
    Play.received += 1;
    Play.queue.push({ m, n: Play.received });
    if (!Play.playing) Play.pump();
  },

  // Ждёт снимок, в котором учтено n-е сообщение (движок шлёт его следом).
  async caughtUp(n) {
    const deadline = Date.now() + 1500;
    while (Play.covered < n && Date.now() < deadline) {
      await new Promise((done) => {
        Play.waiters.push(done);
        setTimeout(done, 200);
      });
    }
  },

  // Рисует последний снимок, если он новее нарисованного.
  sync() {
    if (Play.latest !== undefined) {
      render(Play.latest);
      Play.latest = undefined;
    }
  },

  async pump() {
    Play.playing = true;
    $("table").classList.add("busy");
    while (Play.queue.length) {
      const { m, n } = Play.queue.shift();
      try {
        if (OPENS.has(m.type)) {
          await Play.caughtUp(n);
          Play.sync();
        }
        await animate(m);
      } catch (error) {
        console.error(error);
      }
    }
    Play.playing = false;
    $("table").classList.remove("busy");
    Play.sync();
  },
};

const wait = (ms) => new Promise((done) => setTimeout(done, ms));

// Сообщения, после которых на столе новое состояние: сначала рисуем его.
const OPENS = new Set(["game_started", "round_started", "spread_started", "loaded"]);

// Сообщения, которые видно по самому столу, без подписи.
const QUIET = new Set(["prepared", "effect_removed", "joined", "left",
  "settings_changed", "reconnected", "game_started", "spread_started",
  "spread_ended", "round_started"]);

async function animate(m) {
  switch (m.type) {
    case "shot": return shot(m);
    case "died": return died(m);
    case "turn_passed": return turnPassed(m);
    case "loaded": return loaded(m);
    case "round_ended":
      bubble("победа в раунде", "win", m.winner);
      return wait(1500);
    case "chip_earned":
      bubble(caption(m), "", m.player);
      return wait(350);
    case "effect_added":
      bubble(caption(m), "", m.owner);
      return wait(500);
  }
  if (ITEM_TARGETS[m.type]) return itemUsed(m);
  if (!QUIET.has(m.type)) {
    bubble(caption(m), "", m.player ?? m.actor ?? null);
    return wait(300);
  }
}

// Выстрел: камора вздрагивает и вскрывается; попадание — вспышка, тряска
// стола, гаснут огоньки жизни.
async function shot(m) {
  const chamber = find(`.chamber[data-chamber="${m.chamber}"]`);
  const seat = seatOf(m.target);
  if (chamber) {
    chamber.classList.remove("picked", "live");
    chamber.classList.add("fire");
  }
  await wait(350);
  if (chamber) chamber.classList.add(m.loaded ? "loaded" : "blank");
  bubble(caption(m), m.loaded && m.damage ? "hit" : "", m.target);
  if (!m.loaded) return wait(650);
  if (m.damage === 0) {
    if (seat) seat.classList.add("shielded");
    return wait(900);
  }
  flash();
  find(".board")?.classList.add("shake");
  if (seat) {
    seat.classList.add("hit");
    const lit = [...seat.querySelectorAll(".life:not(.lost)")];
    for (const life of lit.slice(-m.damage)) life.classList.add("dying");
  }
  await wait(1000);
  find(".board")?.classList.remove("shake");
}

async function died(m) {
  bubble(caption(m), "hit", m.player);
  seatOf(m.player)?.classList.add("dying");
  return wait(1000);
}

// Метка хода бежит по ободу к следующему игроку.
async function turnPassed(m) {
  const marker = find(".turn-marker");
  const round = ui.view && ui.view.round;
  if (!marker || !round || !round.circle.includes(m.active)) return;
  const from = parseFloat(marker.style.getPropertyValue("--a"));
  let to = seatDeg(round, m.active);
  while (to < from) to += 360;
  marker.style.setProperty("--from", `${from}deg`);
  marker.style.setProperty("--a", `${to}deg`);
  marker.classList.remove("moving");
  void marker.offsetWidth;  // перезапуск анимации
  marker.classList.add("moving");
  for (const seat of document.querySelectorAll(".seat.active")) seat.classList.remove("active");
  await wait(450);
  seatOf(m.active)?.classList.add("active");
  return wait(200);
}

// Заряжание: каморы ложатся на стол одна за другой, число патронов
// вспыхивает и гаснет — дальше его держат в голове.
async function loaded(m) {
  const row = find(".row");
  if (!row) return;
  row.querySelectorAll(".chamber").forEach((c, i) => {
    c.style.setProperty("--i", i);
    c.classList.add("deal");
  });
  row.append(el("div", { class: "announced" }, m.announced));
  return wait(1800);
}

// Предмет: значок летит от применившего к тому, на что он действует.
const ITEM_TARGETS = {
  weight_seen: (m) => chamberOf(m.chamber),
  weights_seen: () => find(".row"),
  reversed: (m) => chamberOf(m.chamber),
  cartridge_added: () => find(".row"),
  cartridge_removed: () => find(".row"),
  peeked: (m) => chamberOf(m.chamber),
  shaken: () => find(".row"),
  healed: (m) => seatOf(m.actor),
  gambled: (m) => seatOf(m.actor),
  passed: (m) => seatOf(m.actor),
  item_stolen: (m) => seatOf(m.victim),
  chip_stolen: (m) => seatOf(m.victim),
  jackpot: (m) => seatOf(m.actor),
  wasted: (m) => seatOf(m.actor),
};

const MESSAGE_ITEM = {
  weight_seen: "one-eye", weights_seen: "wide-eyes", reversed: "reverse",
  cartridge_added: "more", cartridge_removed: "scared", peeked: "peek",
  shaken: "shake", gambled: "dubious", passed: "pass", item_stolen: "share",
  chip_stolen: "share", jackpot: "jackpot",
};

async function itemUsed(m) {
  const item = MESSAGE_ITEM[m.type] || m.item;
  const from = seatOf(m.actor);
  const to = ITEM_TARGETS[m.type](m);
  if (from && to) await fly(item, from, to);
  if (m.type === "peeked") chamberOf(m.chamber)?.classList.add(m.loaded ? "loaded" : "blank");
  if (m.type === "shaken" || m.type === "reversed") to?.classList.add("shaken");
  bubble(caption(m), "", m.actor);
  return wait(600);
}

function fly(item, from, to) {
  const box = $("table").getBoundingClientRect();
  const center = (node) => {
    const r = node.getBoundingClientRect();
    return { x: r.left + r.width / 2 - box.left, y: r.top + r.height / 2 - box.top };
  };
  const a = center(from), b = center(to);
  const node = el("span", {
    class: `flying item ${ITEM_CLASS[item] || ""}`,
    style: `left:${a.x}px;top:${a.y}px`,
  }, icon(item));
  layer.append(node);
  const run = node.animate([
    { transform: "translate(-50%, -50%) scale(0.6)", opacity: 0 },
    { transform: "translate(-50%, -50%) scale(1.3)", opacity: 1, offset: 0.2 },
    { transform: `translate(calc(-50% + ${b.x - a.x}px), calc(-50% + ${b.y - a.y}px)) scale(1)`, opacity: 1, offset: 0.85 },
    { transform: `translate(calc(-50% + ${b.x - a.x}px), calc(-50% + ${b.y - a.y}px)) scale(1.6)`, opacity: 0 },
  ], { duration: 750, easing: "ease-in-out" });
  return run.finished.then(() => node.remove());
}

// Вспышка выстрела на весь экран.
function flash() {
  const node = el("div", { class: "flash" });
  document.body.append(node);
  setTimeout(() => node.remove(), 600);
}

function find(selector) {
  return $("table").querySelector(selector);
}

function seatOf(player) {
  return player === null || player === undefined ? null : find(`.seat[data-player="${player}"]`);
}

function chamberOf(i) {
  return find(`.chamber[data-chamber="${i}"]`);
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

// Слой подписей и летящих значков: живёт поверх стола и переживает перерисовку.
const layer = el("div", { class: "bubbles" });

function bubble(text, kind, playerId) {
  const table = $("table");
  const seat = seatOf(playerId);
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
