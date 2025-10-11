"""
Обработчики сообщений бота.
Импортируются для регистрации декораторов.

ВАЖНО: Порядок импорта имеет значение!
Специфичные хендлеры (rent, search, subscriptions) должны быть ПЕРЕД общими (menu).
"""
# Импортируем в правильном порядке: от специфичных к общим
from . import wall_events   # Обработчики событий со стены (публикация постов)
from . import rent          # Специфичные хендлеры для создания объявлений
from . import search        # Специфичные хендлеры для поиска
from . import subscriptions # Специфичные хендлеры для подписок
from . import contract      # Специфичные хендлеры для проверки договоров
from . import menu          # Общие хендлеры (menu, start, fallback) - ПОСЛЕДНИМ!

__all__ = ["wall_events", "rent", "search", "subscriptions", "contract", "menu"]
