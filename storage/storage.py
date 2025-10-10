"""
Постоянное хранилище данных бота.
Сохраняет счетчики поисков и другие данные пользователей.
"""
import json
import os
import logging
from typing import Dict, Any, List, Optional
from threading import Lock

from bot.config import STORAGE_FILE

logger = logging.getLogger("storage")

# Блокировка для потокобезопасности
_lock = Lock()


def _load_storage() -> Dict[str, Any]:
    """Загружает данные из JSON файла."""
    if not os.path.exists(STORAGE_FILE):
        return {
            "user_search_count": {},
            "user_data": {},
            "user_subscriptions": {},  # {user_id: [subscription_obj, ...]}
            "last_checked_post_id": None,  # ID последнего проверенного поста
        }

    try:
        with open(STORAGE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Конвертируем строковые ключи обратно в int
            if "user_search_count" in data:
                data["user_search_count"] = {
                    int(k): v for k, v in data["user_search_count"].items()
                }
            return data
    except Exception as e:
        logger.exception("Error loading storage: %s", e)
        return {"user_search_count": {}, "user_data": {}}


def _save_storage(data: Dict[str, Any]) -> None:
    """Сохраняет данные в JSON файл."""
    try:
        # Конвертируем int ключи в строки для JSON
        data_to_save = data.copy()
        if "user_search_count" in data_to_save:
            data_to_save["user_search_count"] = {
                str(k): v for k, v in data_to_save["user_search_count"].items()
            }

        with open(STORAGE_FILE, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.exception("Error saving storage: %s", e)


class Storage:
    """Класс для работы с постоянным хранилищем."""

    def __init__(self):
        self._data = _load_storage()

    def get_search_count(self, user_id: int) -> int:
        """Получает количество поисков пользователя."""
        with _lock:
            return self._data["user_search_count"].get(user_id, 0)

    def increment_search_count(self, user_id: int) -> int:
        """Увеличивает счетчик поисков и возвращает новое значение."""
        with _lock:
            current = self._data["user_search_count"].get(user_id, 0)
            self._data["user_search_count"][user_id] = current + 1
            _save_storage(self._data)
            return current + 1

    def reset_search_count(self, user_id: int) -> None:
        """Сбрасывает счетчик поисков пользователя."""
        with _lock:
            self._data["user_search_count"].pop(user_id, None)
            _save_storage(self._data)

    def get_all_search_counts(self) -> Dict[int, int]:
        """Возвращает все счетчики поисков."""
        with _lock:
            return self._data["user_search_count"].copy()

    def clear_all_search_counts(self) -> None:
        """Очищает все счетчики поисков (для админских целей)."""
        with _lock:
            self._data["user_search_count"] = {}
            _save_storage(self._data)

    # === Методы для работы с подписками ===

    def add_subscription(self, user_id: int, filters: Dict[str, Any]) -> str:
        """
        Добавляет подписку пользователя на параметры поиска.

        Args:
            user_id: ID пользователя
            filters: Фильтры поиска

        Returns:
            ID созданной подписки
        """
        import uuid
        import time

        with _lock:
            if "user_subscriptions" not in self._data:
                self._data["user_subscriptions"] = {}

            user_subs = self._data["user_subscriptions"].get(str(user_id), [])

            subscription = {
                "id": str(uuid.uuid4())[:8],
                "filters": filters,
                "created_at": int(time.time()),
                "enabled": True,
            }

            user_subs.append(subscription)
            self._data["user_subscriptions"][str(user_id)] = user_subs
            _save_storage(self._data)

            return subscription["id"]

    def get_user_subscriptions(self, user_id: int) -> List[Dict[str, Any]]:
        """Получает все подписки пользователя."""
        with _lock:
            if "user_subscriptions" not in self._data:
                return []
            return self._data["user_subscriptions"].get(str(user_id), []).copy()

    def toggle_subscription(self, user_id: int, sub_id: str) -> bool:
        """
        Переключает состояние подписки (вкл/выкл).

        Returns:
            Новое состояние подписки (True = включена)
        """
        with _lock:
            if "user_subscriptions" not in self._data:
                return False

            user_subs = self._data["user_subscriptions"].get(str(user_id), [])

            for sub in user_subs:
                if sub["id"] == sub_id:
                    sub["enabled"] = not sub.get("enabled", True)
                    _save_storage(self._data)
                    return sub["enabled"]

            return False

    def delete_subscription(self, user_id: int, sub_id: str) -> bool:
        """Удаляет подписку пользователя."""
        with _lock:
            if "user_subscriptions" not in self._data:
                return False

            user_subs = self._data["user_subscriptions"].get(str(user_id), [])
            new_subs = [s for s in user_subs if s["id"] != sub_id]

            if len(new_subs) < len(user_subs):
                self._data["user_subscriptions"][str(user_id)] = new_subs
                _save_storage(self._data)
                return True

            return False

    def get_all_active_subscriptions(self) -> List[tuple]:
        """
        Получает все активные подписки всех пользователей.

        Returns:
            Список кортежей (user_id, subscription)
        """
        with _lock:
            if "user_subscriptions" not in self._data:
                return []

            result = []
            for user_id_str, subs in self._data["user_subscriptions"].items():
                for sub in subs:
                    if sub.get("enabled", True):
                        result.append((int(user_id_str), sub))

            return result

    def get_last_checked_post_id(self) -> Optional[int]:
        """Получает ID последнего проверенного поста."""
        with _lock:
            return self._data.get("last_checked_post_id")

    def set_last_checked_post_id(self, post_id: int) -> None:
        """Сохраняет ID последнего проверенного поста."""
        with _lock:
            self._data["last_checked_post_id"] = post_id
            _save_storage(self._data)


# Создаем глобальный экземпляр
storage = Storage()
