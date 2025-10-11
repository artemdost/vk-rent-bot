"""
Конфигурация бота и настройки окружения.
Здесь хранятся все переменные окружения и константы.
"""
import os
import logging
from dotenv import load_dotenv

load_dotenv()

# Логирование
LOG = logging.getLogger("bot")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)

# VK API конфигурация
USER_TOKEN = os.getenv("USER_TOKEN") or os.getenv("VK_TOKEN")
GROUP_TOKEN = os.getenv("GROUP_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID") or 0)
API_V = os.getenv("VK_API_VERSION", "5.199")
UPLOAD_TOKEN = os.getenv("UPLOAD_TOKEN")
VK_CONFIRMATION_KEY = os.getenv("VK_CONFIRMATION_KEY", "")

# Выбираем токен для бота (предпочитаем user-token)
TOKEN_FOR_BOT = USER_TOKEN or GROUP_TOKEN

if not TOKEN_FOR_BOT:
    raise RuntimeError("Нужен USER_TOKEN (или VK_TOKEN) или GROUP_TOKEN в .env")

LOG.info("Starting bot: using %s", "USER_TOKEN" if USER_TOKEN else "GROUP_TOKEN")

# Настройки бота
SUPPORT_URL = os.getenv("SUPPORT_URL", "https://vk.com/")
MAX_SEARCHES_UNSUBSCRIBED = int(os.getenv("MAX_SEARCHES_UNSUBSCRIBED", "3"))
SEARCH_RESULTS_LIMIT = int(os.getenv("SEARCH_RESULTS_LIMIT", "30"))
SEARCH_RESULTS_PAGE_SIZE = 10

# Настройки постинга
DEFAULT_SCHEDULE_DELAY = 2 * 24 * 60 * 60  # 2 дня
REQUEST_TIMEOUT = 30

# Настройки хранилища
STORAGE_FILE = os.getenv("STORAGE_FILE", "bot_storage.json")

# Текстовые константы
MENU_GREETING = "Привет! Выберите действие:"
START_COMMANDS = {"/start", "start", "начать", "старт"}

# Временные настройки
ALLOW_GREETING_SUPPRESS_SECONDS = 5.0
