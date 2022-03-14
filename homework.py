import logging
import os
import sys
import time
from http import HTTPStatus

from dotenv import load_dotenv
from telegram import Bot
import requests

from exceptions import MissValueError, ServerUnavailabilityError

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(stream=sys.stdout)
formatter = logging.Formatter(
    '%(asctime)s [%(levelname)s] %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 10
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляет сообщение в чат указанному пользователю."""
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    logger.info(f'Бот отправил сообщение "{message}"')


def get_api_answer(current_timestamp):
    """Получает ответ от API-сервиса в виде словаря Python."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    logger.debug(
        'Запрос к серверу '
        'https://practicum.yandex.ru/api/user_api/homework_statuses/...'
    )
    api_answer = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if api_answer.status_code != HTTPStatus.OK:
        raise ServerUnavailabilityError(
            'Эндпоинт '
            'https://practicum.yandex.ru/api/user_api/homework_statuses/ '
            f'недоступен. Код ответа API: {api_answer.status_code}'
        )
    logger.info(
        'Запрос к серверу '
        'https://practicum.yandex.ru/api/user_api/homework_statuses/ '
        f'прошел успешно. Код ответа {api_answer.status_code}'
    )
    return api_answer.json()


def check_response(response):
    """Проверяет ответ от API-сервиса на корректность."""
    if type(response) != dict:
        raise TypeError('Неверный ответ от API сервиса')
    if 'homeworks' not in response:
        raise MissValueError('Отсутствует ожидаемый ключ в ответе API')
    homeworks = response.get('homeworks')
    if type(homeworks) != list:
        raise TypeError('Неверный формат списка домашних работ')
    return response.get('homeworks')


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работы статус
    этой работы.
    """
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if HOMEWORK_STATUSES.get(homework_status):
        verdict = HOMEWORK_STATUSES.get(homework_status)
    else:
        raise KeyError(f'Статуса {homework_status} не существует!')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных PRACTICUM_TOKEN, TELEGRAM_TOKEN
    и TELEGRAM_CHAT_ID.
    """
    return (
        bool(PRACTICUM_TOKEN) * bool(TELEGRAM_TOKEN) * bool(TELEGRAM_CHAT_ID)
    )


def main():
    """Основная логика работы бота."""
    loggers = {
        PRACTICUM_TOKEN:
        'Отсутствует обязательная переменная окружения: '
        'PRACTICUM_TOKEN. Программа принудительно остановлена.',
        TELEGRAM_TOKEN:
        'Отсутствует обязательная переменная окружения: '
        'TELEGRAM_TOKEN. Программа принудительно остановлена.',
        TELEGRAM_CHAT_ID:
        'Отсутствует обязательная переменная окружения: '
        'TELEGRAM_CHAT_ID. Программа принудительно остановлена.'
    }
    for variable, error in loggers.items():
        if not variable:
            logger.critical(error)
            raise MissValueError(error)

    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    previous_error_message = ''

    while True:
        try:
            response = get_api_answer(current_timestamp)
            current_homework_list = check_response(response)
            if len(current_homework_list) == 0:
                logger.debug('Новые статусы отсутствуют')
            else:
                for current_homework in current_homework_list:
                    send_message(bot, parse_status(current_homework))
            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if previous_error_message != message:
                send_message(bot, message)
                previous_error_message = message
            time.sleep(RETRY_TIME)
        else:
            logger.info('Цикл работы программы завершен успешно')


if __name__ == '__main__':
    main()
