# storage.py
import json
import os
import logging
from typing import Dict, Any
from threading import Lock

logger = logging.getLogger("storage")

STORAGE_FILE = os.getenv("STORAGE_FILE", "bot_storage.json")

# Блокировка для потокобезопасности
_lock = Lock()


def _load_storage() -> Dict[str, Any]:
    """Загружает данные из JSON файла."""
    if not os.path.exists(STORAGE_FILE):
        return {"user_search_count": {}, "user_data": {}}
    
    try:
        with open(STORAGE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Конвертируем строковые ключи обратно в int для user_search_count
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


# Создаем глобальный экземпляр
storage = Storage()