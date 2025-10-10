"""
Сервис для работы с VK API.
Содержит низкоуровневые функции для вызова методов API.
"""
import logging
import requests
from typing import Dict, Any, Optional, List
from vkbottle.bot import Message

from bot.config import TOKEN_FOR_BOT, API_V, REQUEST_TIMEOUT

logger = logging.getLogger("vk_api")


def vk_api_call(
    method: str,
    params: Dict[str, Any],
    token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Универсальный вызов VK API методом POST.

    Args:
        method: Название метода VK API
        params: Параметры запроса
        token: Access token (если не указан, используется TOKEN_FOR_BOT)

    Returns:
        Распарсенный JSON ответ
    """
    url = f"https://api.vk.com/method/{method}"
    payload = dict(params)
    access_token = token or TOKEN_FOR_BOT

    if access_token:
        payload.setdefault("access_token", access_token)
    payload.setdefault("v", API_V)

    try:
        response = requests.post(url, data=payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        logger.exception("VK API call failed for %s: %s", method, exc)
        return {"error": {"error_msg": str(exc)}}


async def extract_photo_urls_from_message(message: Message) -> List[str]:
    """
    Извлекает URL всех фото из сообщения.

    Args:
        message: Объект сообщения VKbottle

    Returns:
        Список URL фотографий
    """
    try:
        full_msg = await message.get_full_message()
    except Exception:
        full_msg = None

    candidate_sources = []

    if full_msg and getattr(full_msg, "attachments", None):
        candidate_sources.append(full_msg.attachments)
    if getattr(message, "attachments", None):
        candidate_sources.append(message.attachments)
    if full_msg:
        raw_atts = getattr(full_msg, "__dict__", {}).get("attachments")
        if raw_atts and raw_atts not in candidate_sources:
            candidate_sources.append(raw_atts)
    raw_current = getattr(message, "__dict__", {}).get("attachments")
    if raw_current and raw_current not in candidate_sources:
        candidate_sources.append(raw_current)

    raw_payload = getattr(message, "dict", None)
    if callable(raw_payload):
        try:
            attachments_dict = raw_payload().get("attachments")
            if attachments_dict and attachments_dict not in candidate_sources:
                candidate_sources.append(attachments_dict)
        except Exception:
            pass

    urls: List[str] = []
    seen: set = set()

    for source in candidate_sources:
        items = list(source or [])
        for a in items:
            try:
                photo = getattr(a, "photo", None)
                if photo is None and isinstance(a, dict):
                    photo = a.get("photo")
                if not photo:
                    continue

                if hasattr(photo, "model_dump"):
                    photo_data = photo.model_dump()
                elif isinstance(photo, dict):
                    photo_data = photo
                else:
                    photo_data = {
                        key: getattr(photo, key)
                        for key in dir(photo)
                        if not key.startswith("_")
                    }

                added = False
                size_candidates = photo_data.get("sizes") or []

                if size_candidates:
                    if isinstance(size_candidates, dict):
                        size_candidates = size_candidates.values()

                    for size in list(size_candidates)[::-1]:
                        if isinstance(size, dict):
                            url = size.get("url")
                        else:
                            url = getattr(size, "url", None)

                        if url:
                            if url not in seen:
                                urls.append(url)
                                seen.add(url)
                            added = True
                            break

                if not added:
                    for key, value in photo_data.items():
                        if isinstance(value, str) and value.startswith("http"):
                            if value not in seen:
                                urls.append(value)
                                seen.add(value)
                            added = True
                            break
            except Exception:
                continue

    return urls
