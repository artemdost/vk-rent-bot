"""
Утилиты для форматирования текста и данных.
"""
import re
from typing import Any, Dict, List


def format_price_display(value: Any) -> str:
    """Форматирует цену для отображения."""
    if value is None:
        return "—"
    try:
        if isinstance(value, str):
            digits = re.sub(r"\D", "", value)
            if not digits:
                return value
            numeric = int(digits)
        else:
            numeric = int(value)
    except (TypeError, ValueError):
        return str(value)

    formatted = format(numeric, ",").replace(",", ".")
    return f"{formatted} ₽"


def build_post_text(draft: Dict[str, Any]) -> str:
    """Создает текст поста из черновика объявления."""
    parts: List[str] = []

    if draft.get("price") is not None:
        parts.append(f"💰 Цена: {format_price_display(draft.get('price'))}")
    if draft.get("district"):
        parts.append(f"🏙 Район: {draft.get('district')}")
    if draft.get("address"):
        parts.append(f"📍 Адрес: {draft.get('address')}")
    if draft.get("floor") is not None:
        parts.append(f"🏢 Этаж: {draft.get('floor')}")
    if draft.get("rooms") is not None:
        parts.append(f"🚪 Комнат: {draft.get('rooms')}")

    if draft.get("description"):
        parts.append("")
        parts.append(draft.get("description"))

    parts.append("")
    if draft.get("fio"):
        parts.append(f"👤 Контакт: {draft.get('fio')}")
    if draft.get("phone"):
        parts.append(f"📞 Телефон: {draft.get('phone')}")

    return "\n".join(parts).strip()


def format_preview_text(draft: Dict[str, Any]) -> str:
    """Форматирует текст предпросмотра объявления."""
    price_formatted = format_price_display(draft.get("price"))

    return (
        f"📌 Предпросмотр объявления:\n\n"
        f"💰 Цена: {price_formatted}\n"
        f"🏙 Район: {draft.get('district','—')}\n"
        f"📍 Адрес: {draft.get('address','—')}\n"
        f"🏢 Этаж: {draft.get('floor','—')}\n"
        f"🚪 Комнат: {draft.get('rooms','—')}\n"
        f"📝 Описание:\n{draft.get('description','—')}\n\n"
        f"👤 Контакт: {draft.get('fio','—')}\n"
        f"📞 Телефон: {draft.get('phone','—')}\n\n"
        "Нажмите «Отправить», чтобы поставить объявление в отложенные записи сообщества, "
        "или выберите «Изменить ...», чтобы редактировать поле."
    )


def format_search_result(index: int, item: Dict[str, Any]) -> str:
    """Форматирует результат поиска."""
    post_id = item.get("id")
    if post_id is None:
        return f"Объявление №{index}"
    return f"Объявление №{index}"
