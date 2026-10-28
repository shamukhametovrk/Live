// Соединение с движком: JSON по WebSocket, снимок после сообщений,
// возврат за стол по токену.

const Net = {
  server: null,
  ws: null,
  me: null,         // номер игрока, если сели за стол
  waiting: false,   // ждём ответа на запрос снимка
  dirty: false,     // после запроса пришли новые сообщения
  greeting: false,  // ждём снимок, который движок шлёт при подключении
  onSnapshot: () => {},
  onLine: () => {},

  connect(server) {
    this.server = server;
    const saved = this.saved();
    this.me = saved ? saved.player : null;
    // За HTTPS браузер пускает только защищённый сокет.
    const scheme = location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${scheme}://${server}/ws`);
    this.ws = ws;
    ws.onopen = () => {
      setStatus(`подключено к ${server}`);
      if (saved) this.send({ type: "resume", token: saved.token });
    };
    ws.onmessage = (e) => this.receive(JSON.parse(e.data));
    ws.onclose = () => {
      if (this.ws !== ws) return;
      setStatus("нет связи, переподключаемся…");
      setTimeout(() => this.connect(server), 1500);
    };
  },

  send(obj) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(obj));
    }
  },

  askSnapshot() {
    this.waiting = true;
    this.dirty = false;
    this.send({ type: "snapshot" });
  },

  receive(data) {
    switch (data.type) {
      case "welcome":
        if (this.me === null) this.client = data.client;
        this.greeting = true;  // следом — снимок до ответа на resume
        break;
      case "token":
        this.me = this.client;
        localStorage.setItem(this.key(), JSON.stringify({
          token: data.token, player: this.me,
        }));
        break;
      case "message":
        this.onLine(describe(data.message), data.message.type);
        this.dirty = true;
        if (!this.waiting) this.askSnapshot();
        break;
      case "rejected":
        this.onLine(REJECTIONS[data.code] || data.code, "rejected");
        if (data.code === "bad_token") this.forget();
        break;
      case "snapshot":
        this.waiting = false;
        if (this.dirty) { this.askSnapshot(); break; }
        // Пустой стол у севшего — стол очищен, места больше нет.
        if (this.greeting) this.greeting = false;
        else if (data.view === null && this.me !== null) this.forget();
        this.onSnapshot(data.view);
        break;
      case "history":
        this.onLine(`история: ${data.events.length} событий (в консоли браузера)`);
        console.log(data.events);
        break;
    }
  },

  forget() {
    localStorage.removeItem(this.key());
    this.me = null;
  },

  key() { return `live-token:${this.server}`; },
  saved() {
    try { return JSON.parse(localStorage.getItem(this.key())); }
    catch { return null; }
  },
};

function setStatus(text) {
  document.getElementById("status").textContent = text;
}
