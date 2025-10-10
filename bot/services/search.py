"""
Сервис для поиска объявлений в сообществе.
"""
import re
import time
import logging
from typing import Dict, Any, List, Optional, Tuple

from bot.config import (
    GROUP_ID,
    USER_TOKEN,
    UPLOAD_TOKEN,
    SEARCH_RESULTS_LIMIT,
)
from bot.services.vk_api import vk_api_call

logger = logging.getLogger("search")


# Метки полей для парсинга постов
FIELD_LABELS = {
    "district": "Район",
    "address": "Адрес",
    "floor": "Этаж",
    "rooms": "Комнат",
    "price": "Цена",
    "fio": "Контакт",
    "phone": "Телефон",
}


def parse_post_text(text: str) -> Dict[str, Any]:
    """
    Парсит текст поста и извлекает структурированные данные.

    Args:
        text: Текст поста

    Returns:
        Словарь с извлечёнными данными
    """
    parsed: Dict[str, Any] = {}
    if not text:
        return parsed

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue

        for key, label in FIELD_LABELS.items():
            marker = f"{label}:"
            if marker in line:
                value = line.split(marker, 1)[1].strip()
                parsed[key] = value

                # Извлекаем числовые значения
                if key in {"price", "rooms", "floor"}:
                    digits = re.sub(r"\D", "", value)
                    if digits:
                        parsed[f"{key}_value"] = int(digits)
                break

    return parsed


def search_posts(
    filters: Dict[str, Any],
    limit: Optional[int] = None,
    fetch_count: int = 100,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Ищет посты в сообществе по заданным фильтрам.

    Args:
        filters: Словарь фильтров (district, price_min, price_max, rooms, recent_days)
        limit: Максимальное количество результатов
        fetch_count: Количество постов для загрузки за раз

    Returns:
        (список найденных постов, сообщение об ошибке или None)
    """
    if not GROUP_ID:
        return [], "GROUP_ID не настроен"

    owner_id = -abs(int(GROUP_ID))
    payload = {
        "owner_id": owner_id,
        "count": fetch_count,
        "offset": 0,
    }

    token_for_wall = USER_TOKEN or UPLOAD_TOKEN
    if not token_for_wall:
        return [], "Добавьте USER_TOKEN или UPLOAD_TOKEN с правами wall/groups для поиска по постам"

    resp = vk_api_call("wall.get", payload, token=token_for_wall)

    if "error" in resp:
        err_msg = resp["error"].get("error_msg", "Неизвестная ошибка VK")
        if err_msg.lower().startswith("group authorization failed"):
            err_msg = "Токен не подходит для wall.get. Убедитесь, что USER_TOKEN или UPLOAD_TOKEN выданы администратору с правами wall,groups."
        return [], err_msg

    items = resp.get("response", {}).get("items", [])
    if not isinstance(items, list):
        return [], "Некорректный ответ от VK"

    target_limit = limit if limit is not None else SEARCH_RESULTS_LIMIT
    if target_limit is not None and target_limit <= 0:
        target_limit = None

    # Фильтр по дате
    recent_days_filter = filters.get("recent_days")
    if isinstance(recent_days_filter, str):
        try:
            recent_days_filter = int(recent_days_filter.strip())
        except ValueError:
            recent_days_filter = None

    recent_threshold: Optional[float] = None
    if isinstance(recent_days_filter, int) and recent_days_filter > 0:
        recent_threshold = time.time() - recent_days_filter * 86400

    # Остальные фильтры
    district_filter = filters.get("district")
    price_min = filters.get("price_min")
    price_max = filters.get("price_max")
    rooms_filter = filters.get("rooms")

    matches: List[Dict[str, Any]] = []

    for item in items:
        # Фильтр по дате
        if recent_threshold is not None:
            item_date = item.get("date")
            if isinstance(item_date, str):
                try:
                    item_date = int(item_date.strip())
                except ValueError:
                    item_date = None

            if not isinstance(item_date, (int, float)):
                continue
            if item_date < recent_threshold:
                continue

        # Парсим текст
        text = item.get("text", "")
        parsed = parse_post_text(text)
        if not parsed:
            continue

        # Фильтр по району
        if district_filter:
            district = parsed.get("district")
            if not district or district.lower() != district_filter.lower():
                continue

        # Фильтр по цене
        price_value = parsed.get("price_value")
        if price_min is not None:
            if price_value is None or price_value < price_min:
                continue
        if price_max is not None:
            if price_value is None or price_value > price_max:
                continue

        # Фильтр по комнатам
        rooms_value = parsed.get("rooms_value")
        if rooms_filter is not None:
            if rooms_value is None or rooms_value != rooms_filter:
                continue

        matches.append({"item": item, "parsed": parsed})

        if target_limit is not None and len(matches) >= target_limit:
            break

    # Сортируем по дате (старые первые)
    matches.sort(key=lambda x: x["item"].get("date", 0), reverse=False)

    return matches, None
