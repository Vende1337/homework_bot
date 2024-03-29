from http import HTTPStatus
import logging
import os
import time
import sys

import requests
from telegram import Bot, TelegramError
from dotenv import load_dotenv

from exceptions import (NotSendingError, SendMessageError,
                        RequestAPIError, HTTPError, CurrentTimeError)


load_dotenv()

logger = logging.getLogger(__name__)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """
    Отправляет сообщение в Telegram чат.
    определяемый переменной окружения TELEGRAM_CHAT_ID.
    Принимает на вход два параметра:
    экземпляр класса Bot и строку с текстом сообщения.
    """
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except TelegramError as error:
        raise SendMessageError(
            f'Сбой при отправке сообщения.{error}')
    else:
        logger.info('Сообщение отправлено')


def get_api_answer(current_timestamp):
    """
    Делает запрос к единственному эндпоинту API-сервиса.
    В качестве параметра функция получает временную метку.
    В случае успешного запроса должна вернуть ответ API,
    преобразовав его из формата JSON к типам данных Python.
    """
    params = {'from_date': current_timestamp}
    try:
        homework_statuses = requests.get(
            ENDPOINT, headers=HEADERS, params=params)
        if homework_statuses.status_code != HTTPStatus.OK:
            raise HTTPError(
                f'Сбои при запросе к эндпоинту{homework_statuses.status_code}')
        return homework_statuses.json()
    except requests.RequestException as error:
        raise RequestAPIError(
            f'Ошибка при запросе к Эндпоинту:{error}')


def check_response(response):
    """
    Проверяет ответ API на корректность.
    В качестве параметра функция получает ответ API,
    приведенный к типам данных Python.
    Если ответ API соответствует ожиданиям,
    то функция должна вернуть список домашних работ
    (он может быть и пустым), доступный в ответе API по ключу 'homeworks'.
    """
    if not isinstance(response, dict):
        raise TypeError('Ответ API не является словарем')
    if 'homeworks' not in response:
        raise KeyError('В ответе API отсутствует домашняя работа')
    if not isinstance(response.get('homeworks'), list):
        raise TypeError('Ответ API не является списком')
    if 'current_date' not in response:
        raise CurrentTimeError('В ответе API отсутствует текущее время')
    if not isinstance(response.get('current_date'), int):
        raise CurrentTimeError('current_date не является целым числом')
    return response.get('homeworks')


def parse_status(homework):
    """
    Извлекает из информации о конкретной домашней работе статус этой работы.
    В качестве параметра функция получает только
    один элемент из списка домашних работ.
    В случае успеха, функция возвращает подготовленную
    для отправки в Telegram строку,
    содержащую один из вердиктов словаря HOMEWORK_STATUSES.
    """
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if 'status' not in homework:
        raise KeyError('Отсутствие ожидаемого ключа в ответе API')
    if 'homework_name' not in homework:
        raise KeyError('Отсутствие ожидаемого ключа в ответе API')
    if homework_status not in VERDICTS:
        raise KeyError('Недокументированный статус домашней работы')
    verdict = VERDICTS[homework_status]
    return (f'Изменился статус проверки работы "{homework_name}".'
            f'{verdict}')


def check_tokens():
    """
    Проверяет доступность переменных окружeния.
        которые необходимы для работы программы.
        Если отсутствует хотя бы одна переменная окружения
        — функция должна вернуть False, иначе — True.
    """
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Токены недоступны')
        sys.exit('Токены недоступны')
    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework_answer = check_response(response)
            current_timestamp = response.get('current_date')
            if len(homework_answer) == 0:
                logger.error('Отсутствуют новые статусы домашки')
            else:
                message = parse_status(homework_answer[0])
                send_message(bot, message)
        except NotSendingError as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            try:
                send_message(bot, message)
            except SendMessageError as error:
                logger.error(
                    f'Не удалось отправить сообщение об ошибке:{error}')
            logger.error(message)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s,%(levelname)s,%(message)s,%(funcName)s,%(lineno)d',
        handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(
            filename=os.path.join('main.log'),
            mode='w',
            encoding='UTF-8')])
    main()
