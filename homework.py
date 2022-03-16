import logging
import os
import sys
import time
from http import HTTPStatus

from dotenv import load_dotenv
from telegram import Bot
import requests

from exceptions import (
    ServerUnavailabilityError, WrongApiAnswerError,
    HomeworkListError, MissValueError
)

load_dotenv()

logger = logging.getLogger(__name__)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


STATUS_DESCRIBTIONS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляет сообщение в чат указанному пользователю.

    Ключевые аргументы:
    bot -- объект телеграмм-бота
    message -- строка сообщения
    """
    logger.debug('Бот начал отправку сообщения')
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    logger.info(f'Бот отправил сообщение "{message}"')


def get_api_answer(current_timestamp):
    """Получает ответ от API-сервиса в виде словаря Python.

    Ключевые аргументы:
    current_timestamp -- текущее время
    """
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    logger.debug(f'Запрос к серверу {ENDPOINT}...')
    api_answer = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if api_answer.status_code != HTTPStatus.OK:
        raise ServerUnavailabilityError(
            f'Эндпоинт {ENDPOINT} недоступен. '
            f'Код ответа API: {api_answer.status_code}'
        )
    logger.info(
        f'Запрос к серверу {ENDPOINT} прошел успешно. '
        f'Код ответа {api_answer.status_code}'
    )
    return api_answer.json()


def check_response(response):
    """Проверяет ответ от API-сервиса на корректность.

    Ключевые аргументы:
    response -- словарь с ответами от API
    """
    if not isinstance(response, dict):
        raise TypeError('Формат ответа API не словарь')
    if 'homeworks' not in response or 'current_date' not in response:
        raise WrongApiAnswerError('Ожидаемые ключи в ответе API отсутствуют')
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise HomeworkListError(
            'Домашние работы в ответе API представлены не списком'
        )
    return homeworks


def parse_status(homework):
    """Извлекает статус домашней работы.

    Ключевые аргументы:
    homework -- словарь со значениями по конкретной работе
    """
    if ('homework_name' not in homework
            or 'status' not in homework):
        raise KeyError('Неверный формат данных домашней работы')
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    verdict = STATUS_DESCRIBTIONS.get(homework_status)
    if not verdict:
        raise KeyError(f'Статуса {homework_status} не существует!')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных.

    Ключевые аргументы:
    PRACTICUM_TOKEN
    TELEGRAM_TOKEN
    TELEGRAM_CHAT_ID
    """
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        variables_name_variables = {
            PRACTICUM_TOKEN: 'PRACTICUM_TOKEN',
            TELEGRAM_TOKEN: 'TELEGRAM_TOKEN',
            TELEGRAM_CHAT_ID: 'TELEGRAM_CHAT_ID',
        }
        for variable, name_variable in variables_name_variables.items():
            if not variable:
                message = (
                    'Отсутствует обязательная переменная окружения: '
                    f'{name_variable}. Программа принудительно остановлена.'
                )
                logger.critical(message)
                raise MissValueError(message)

    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    previous_error_message = ''

    while True:
        try:
            response = get_api_answer(current_timestamp)
            current_homework_list = check_response(response)
            if not current_homework_list:
                logger.debug('Новые статусы отсутствуют')
            else:
                for current_homework in current_homework_list:
                    send_message(bot, parse_status(current_homework))
            current_timestamp = int(time.time())
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if previous_error_message != message:
                send_message(bot, message)
                previous_error_message = message
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(stream=sys.stdout)
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    main()
