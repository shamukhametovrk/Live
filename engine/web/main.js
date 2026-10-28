// Запуск: связываем соединение с проигрыванием и экранами.

Net.onSnapshot = Play.snapshot;
Net.onMessage = Play.message;
Net.onRejected = (code) => bubble(REJECTIONS[code] || code, "bad", null);

// Страницу отдаёт сам движок — подключаемся к тому же адресу.
Net.connect(location.host || "localhost:8000");

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && (ui.pending || ui.chamber !== null)) {
    ui.pending = null;
    ui.chamber = null;
    if (ui.view) render(ui.view);
  }
});
