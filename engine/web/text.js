// Русские тексты: предметы, эффекты, отказы и строки ленты.

const ITEMS = {
  "one-eye": "Одним глазом",
  "wide-eyes": "Во все глаза",
  "reverse": "Реверс",
  "more": "Хочу ещё",
  "scared": "Мне страшно",
  "peek": "Что тут у нас",
  "shake": "ХАХхаахХАх",
  "water": "Глоток воды",
  "dubious": "Сомнительное удовольствие",
  "like-new": "Как новый",
  "pass": "Пасс",
  "double": "Дубль",
  "full-force": "Со всей дури",
  "shield": "Настроечный щит",
  "try-this": "Попробуй вот эту",
  "play-along": "Подыграй мне",
  "share": "Пора делиться",
  "jackpot": "Джекпот",
};

// Какие поля предмет требует при применении (см. справочник движка).
const ITEM_FIELDS = {
  "one-eye": ["chamber"],
  "reverse": ["chamber"],
  "peek": ["chamber"],
  "try-this": ["player", "chamber"],
  "play-along": ["player", "target"],
  "share": ["player", "take"],
};

const REJECTIONS = {
  not_your_turn: "Сейчас не ваш ход",
  chamber_used: "Эта камора уже использована",
  no_such_chamber: "Такой каморы нет",
  target_not_alive: "Цель не жива",
  player_not_alive: "Этот игрок не жив",
  must_shoot_named_target: "«Подыграй мне»: стрелять нужно в названного игрока",
  must_use_named_chamber: "«Попробуй вот эту»: нужна названная камора",
  must_name_opponent: "Нужно выбрать соперника",
  item_not_in_hand: "Этого предмета нет в руке",
  hand_over_limit: "В руке не больше 8 предметов",
  hand_not_available: "Таких предметов нет",
  bad_chips: "Нужно разложить все фишки",
  already_prepared: "Решение уже отправлено",
  paused: "Пауза: кто-то без связи",
  not_host: "Это может только хост",
  wrong_number_of_players: "Нужно от 2 до 6 игроков",
  already_joined: "Вы уже за столом",
  table_full: "Стол полон",
  not_joined: "Сначала сядьте за стол",
  game_started: "Игра уже идёт",
  bad_token: "Не удалось вернуться за стол",
  bad_request: "Движок не понял запрос",
};

function effectText(e) {
  switch (e.type) {
    case "double": return "Дубль";
    case "full_force": return "Со всей дури";
    case "shield": return "Щит";
    case "play_along": return `Подыграй: в ${e.target}`;
    case "try_this": return `Попробуй: камора ${e.chamber + 1}`;
    default: return e.type;
  }
}

function itemName(id) {
  return `«${ITEMS[id] || id}»`;
}

// Строка ленты по сообщению движка.
function describe(m) {
  const c = (i) => i + 1;
  switch (m.type) {
    case "joined": return `игрок ${m.player} сел за стол`;
    case "left": return `игрок ${m.player} ушёл`;
    case "settings_changed": return `настройки: раундов ${m.settings.rounds}`;
    case "cancelled": return "хост ушёл — игры не будет";
    case "disconnected": return `игрок ${m.player} потерял связь`;
    case "reconnected": return `игрок ${m.player} вернулся`;
    case "withdrew": return `игрок ${m.player} выбыл`;
    case "game_started": return "игра началась";
    case "round_started": return `== раунд: жизней ${m.start_health}, первым ходит ${m.first}`;
    case "spread_started": return `-- новый ряд: ${m.size} камор`;
    case "prepared": return `игрок ${m.player} решил`;
    case "loaded": return `ряд заряжен, патронов: ${m.announced}`;
    case "spread_ended": return "каморы кончились";
    case "round_ended": return `== раунд выиграл ${m.winner}`;
    case "game_finished": return `игра окончена, победа: ${m.winners.join(", ") || "никто"}`;
    case "shot": {
      const who = m.target === m.shooter ? "себя" : m.target;
      const res = !m.loaded ? "холостой"
        : m.damage === 0 ? "патрон, но щит погасил"
        : `патрон, −${m.damage}`;
      return `${m.shooter} стреляет в ${who} каморой ${c(m.chamber)}: ${res}`;
    }
    case "chip_earned": return `+1 фишка игроку ${m.player}`;
    case "died": return `✝ игрок ${m.player} погиб`;
    case "turn_passed": return `ход ${m.turn}: игрок ${m.active}`;
    case "effect_added": return `на игроке ${m.owner}: ${effectText(m.effect)}`;
    case "effect_removed": return `с игрока ${m.owner} снят: ${effectText(m.effect)}`;
    case "weight_seen":
      return m.weight === null
        ? `${m.actor}: ${itemName("one-eye")} на камору ${c(m.chamber)}`
        : `вес каморы ${c(m.chamber)}: ${m.weight}`;
    case "weights_seen":
      return m.weights === null
        ? `${m.actor}: ${itemName("wide-eyes")}`
        : `веса камор: ${m.weights.join(" ")}`;
    case "reversed": return `${m.actor}: ${itemName("reverse")} камора ${c(m.chamber)}`;
    case "cartridge_added": return `${m.actor}: ${itemName("more")}`;
    case "cartridge_removed": return `${m.actor}: ${itemName("scared")}`;
    case "peeked": return `${m.actor}: камора ${c(m.chamber)} — ${m.loaded ? "патрон" : "пусто"}`;
    case "shaken": return `${m.actor}: ${itemName("shake")}`;
    case "healed": return `${m.actor}: ${itemName(m.item)} +${m.amount}`;
    case "gambled": return `${m.actor}: ${itemName("dubious")} ${m.amount >= 0 ? "+" : ""}${m.amount}`;
    case "passed": return `${m.actor}: ${itemName("pass")}`;
    case "item_stolen": return `${m.actor} забрал у ${m.victim} ${itemName(m.item)}`;
    case "chip_stolen": return `${m.actor} забрал у ${m.victim} фишку`;
    case "jackpot": return `${m.actor}: ${itemName("jackpot")} +3 фишки`;
    case "wasted": return `${m.actor}: ${itemName(m.item)} — впустую`;
    default: return m.type;
  }
}
