"""
Утилиты для валидации данных.
"""
import re
from typing import Optional


def extract_int(text: str) -> Optional[int]:
    """Извлекает целое число из текста."""
    if not text:
        return None

    normalized = text.replace(" ", "")
    digits = re.sub(r"\D", "", normalized)

    if not digits:
        return None

    first_digit_index = next(
        (idx for idx, ch in enumerate(normalized) if ch.isdigit()),
        None
    )

    if first_digit_index is None:
        return None

    sign = -1 if "-" in normalized[:first_digit_index + 1] else 1
    return sign * int(digits)


def validate_phone(text: str) -> tuple[bool, str]:
    """
    Валидирует и нормализует номер телефона.
    Возвращает (is_valid, normalized_phone)
    """
    normalized = re.sub(r"[^\d+]", "", text)

    if normalized.count("+") > 1:
        normalized = normalized.replace("+", "")
        normalized = "+" + normalized

    digits = re.sub(r"\D", "", normalized)

    if len(digits) < 7:
        return False, ""

    return True, normalized


def validate_district(text: str) -> bool:
    """Проверяет, является ли текст валидным районом."""
    valid_districts = {
        "Автозаводский", "Канавинский", "Ленинский", "Московский",
        "Нижегородский", "Приокский", "Советский", "Сормовский"
    }
    return text in valid_districts


def validate_search_district(text: str) -> bool:
    """Проверяет, является ли текст валидным районом для поиска."""
    valid_districts = {
        "Автозаводский", "Канавинский", "Ленинский", "Московский",
        "Нижегородский", "Приокский", "Советский", "Сормовский", "Любой"
    }
    return text in valid_districts
