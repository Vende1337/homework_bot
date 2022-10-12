from http import HTTPStatus
import logging
import os
import time
import requests
import sys

from telegram import Bot
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    filename='main.log',
    filemode='w',
    format='%(asctime)s, %(levelname)s, %(name)s, %(message)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info('Сообщение отправлено')
    except Exception as error:
        logger.error(error, exc_info=True)


def get_api_answer(current_timestamp):
    timestamp = current_timestamp
    params = {'from_date': timestamp}
    homework_statuses = requests.get(
        ENDPOINT, headers=HEADERS, params=params)
    try:
        homework_statuses
    except:
        logger.error('СбоЙ при запросе к эндпоинту')
    if homework_statuses.status_code != HTTPStatus.OK:
        logger.error('Нету доступа к Эндпоинту')
        raise Exception
    return homework_statuses.json()


def check_response(response):
    print(response)
    if type(response) is not dict:
        raise TypeError('Ответ API не является словарем')
    if 'homeworks' not in response:
        raise KeyError('В ответе API отсутствует домашняя работа')
    try:
        homework = response.get('homeworks')[0]
    except IndexError:
        logger.debug('Отсутствие в ответе новых статусов')
        return None
    return response.get('homeworks')[0]


def parse_status(homework):
    try:
        homework_name = homework.get('homework_name')
        homework_status = homework.get('status')
    except:
        logger.error('Отсутствие ожидаемых ключей в ответе API')
        raise KeyError
    else:
        try:
            verdict = HOMEWORK_STATUSES[homework_status]
        except:
            logger.error(
                'Недокументированный статус домашней работы, обнаруженный в ответе API')
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    if all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        logger.debug('Токены доступны')
        return True
    else:
        logger.critical('Токены недоступны')
        return False


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework_answer = check_response(response)
            string = parse_status(homework_answer)
            message = send_message(bot, string)
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            time.sleep(RETRY_TIME)
        else:
            response = get_api_answer(current_timestamp)
            homework_answer = check_response(response)
            string = parse_status(homework_answer)
            message = send_message(bot, string)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()