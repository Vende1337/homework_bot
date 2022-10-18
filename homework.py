from http import HTTPStatus
import logging
import os
import time
import sys
import urllib.error

import requests
from telegram import Bot, error
from dotenv import load_dotenv


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
    except error.BadRequest:
        raise error.BadRequest(
            'Сбой при отправке сообщения, текст сообщения пуст.')
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
    except ConnectionError:
        raise ConnectionError('Нет доступа к Эндпоинту')
    if homework_statuses.status_code != HTTPStatus.OK:
        raise urllib.error.HTTPError('Сбои при запросе к эндпоинту')
    try:
        return homework_statuses.json()
    except requests.exceptions.JSONDecodeError('Сбой декодирования JSON'):
        raise requests.exceptions.JSONDecodeError('Сбой декодирования JSON')


def check_response(response):
    """
    Проверяет ответ API на корректность.
    В качестве параметра функция получает ответ API,
    приведенный к типам данных Python.
    Если ответ API соответствует ожиданиям,
    то функция должна вернуть список домашних работ
    (он может быть и пустым), доступный в ответе API по ключу 'homeworks'.
    """
    if 'current_date' not in response:
        raise KeyError('В ответе API отсутствует текущее время')
    if not isinstance(response, dict):
        raise TypeError('Ответ API не является словарем')
    if 'homeworks' not in response:
        raise KeyError('В ответе API отсутствует домашняя работа')
    if not isinstance(response.get('homeworks'), list):
        raise TypeError('Ответ API не является списком')
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
    if type(homework) == dict:
        homework_name = homework.get('homework_name')
        homework_status = homework.get('status')
        if 'status' not in homework:
            raise KeyError('Отсутствие ожидаемого ключа в ответе API')
        elif 'homework_name' not in homework:
            raise KeyError('Отсутствие ожидаемого ключа в ответе API')
        else:
            verdict = VERDICTS[homework_status]
            return (f'Изменился статус проверки работы "{homework_name}".'
                    f'{verdict}')
    elif homework == []:
        logger.debug('Список домашних работ пуст')
    else:
        last_homework = homework[0]
        homework_name = last_homework.get('homework_name')
        homework_status = last_homework.get('status')
        if 'status' not in last_homework:
            raise KeyError('Отсутствие ожидаемого ключа в ответе API')
        elif 'homework_name' not in last_homework:
            raise KeyError('Отсутствие ожидаемого ключа в ответе API')
        else:
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
    if all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        return True
    else:
        return False


def main():
    """Основная логика работы бота."""
    if check_tokens() is False:
        logger.critical('Токены недоступны')
        sys.exit('Токены недоступны')
    else:
        logger.debug('Токены доступны')
    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    new_current_timestamp = get_api_answer(
        current_timestamp).get('current_date')
    while True:
        try:
            response = get_api_answer(new_current_timestamp)
            homework_answer = check_response(response)
            message = parse_status(homework_answer)
            send_message(bot, message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s,%(levelname)s,%(message)s,%(funcName)s,%(lineno)d',
        handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(
            filename='C:\\Dev1\\homework_bot\\main.log', mode='w',
            encoding='UTF-8')])
    main()
