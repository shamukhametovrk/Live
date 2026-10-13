from engine.core.domain.exceptions import DomainError


class GameError(DomainError):
    """Базовый класс ошибок игры."""


class GameStageError(GameError):
    """Действие недоступно в текущей стадии игры."""


class GameLobbyError(GameError):
    """Не удалось присоединиться: уже в игре или мест нет."""


class GameSettingsError(GameError):
    """Недопустимые настройки хоста."""
