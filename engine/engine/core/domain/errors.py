"""Ошибки домена."""


class IllegalAction(Exception):
    """Команда недопустима; состояние не меняется.

    `code` — короткий машинный код причины, его увидит отправитель.
    """

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code
