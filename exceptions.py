class WithMessageBotError(Exception):
    """Исключения, вызов которых требует отправки сообщения в телеграм."""
    pass


class WithoutMessageBotError(Exception):
    """Исключения, вызов которых не требует отправки сообщения в телеграм."""
    pass


class MissValueError(WithoutMessageBotError):
    """Исключение выбрасывается в случае отстутсвия обязательных переменных."""
    pass


class ServerUnavailabilityError(WithMessageBotError):
    """Исключение выбрасывается при сбоях в запросе к внешнему серверу."""
    pass


class WrongApiAnswerError(WithMessageBotError):
    """Исключение выбрасывается если ожидаемые ключи
    в ответе API отсутствуют.
    """
    pass


class HomeworkListError(WithMessageBotError):
    """Исключение выбрасывается если данные о домашних работах
    представлены не списком.
    """
    pass
