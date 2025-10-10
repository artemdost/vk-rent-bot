"""
Экземпляр бота и глобальные переменные.
Отдельный файл для избежания циклических импортов.
"""
from typing import Optional, Dict, Any
from vkbottle.bot import Bot

from .config import TOKEN_FOR_BOT, GROUP_ID, LOG

# Создаём экземпляр бота
bot = Bot(token=TOKEN_FOR_BOT)

# Workaround: патч для groups.getById
if GROUP_ID:
    try:
        _orig_request = bot.api.request  # type: ignore

        async def _patched_request(method: str, data: Optional[Dict[str, Any]] = None):
            params = dict(data) if data else {}
            if method == "groups.getById":
                if not params.get("group_ids") and not params.get("group_id"):
                    params["group_ids"] = str(GROUP_ID)
            return await _orig_request(method, params)

        bot.api.request = _patched_request  # type: ignore
        LOG.info("Applied groups.getById patch with GROUP_ID=%s", GROUP_ID)
    except Exception as e:
        LOG.warning("Failed to apply groups.getById patch: %s", e)

# In-memory хранилище черновиков пользователей
user_data: dict = {}

# Сессии поиска
search_sessions: Dict[str, Dict[str, Any]] = {}
