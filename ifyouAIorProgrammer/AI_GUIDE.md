# Руководство для работы с AI и нейросетями

Этот документ поможет AI-ассистентам (ChatGPT, Claude, и др.) эффективно работать с кодом проекта.

## 🎯 Цель проекта

VK бот для размещения и поиска объявлений об аренде квартир в Нижнем Новгороде.

## 🏗️ Архитектура проекта

### Принципы организации кода

1. **Модульность** - каждый файл выполняет одну задачу
2. **Слоистая архитектура** - разделение на уровни ответственности
3. **Чистый код** - понятные имена, документация, типизация

### Слои приложения (сверху вниз)

```
User Input
    ↓
[Handlers] - Обработка сообщений, управление FSM
    ↓
[Services] - Бизнес-логика, работа с API
    ↓
[Utils] - Вспомогательные функции
    ↓
[Storage] - Постоянное хранилище
```

## 📂 Карта модулей

### Конфигурация и инициализация

#### `bot/config.py`
**Назначение:** Загрузка env переменных, константы приложения
**Используется:** Везде где нужны настройки
**Основные экспорты:**
- `TOKEN_FOR_BOT`, `GROUP_ID`, `API_V` - VK API настройки
- `MENU_GREETING`, `SUPPORT_URL` - текстовые константы
- `MAX_SEARCHES_UNSUBSCRIBED` - бизнес-логика

#### `bot/__init__.py`
**Назначение:** Инициализация экземпляра бота
**Основные экспорты:**
- `bot` - экземпляр Bot из vkbottle
- `user_data` - in-memory хранилище черновиков
- `search_sessions` - сессии поиска

### Состояния FSM

#### `bot/states.py`
**Назначение:** Определение состояний диалогов
**Основные экспорты:**
- `RentStates` - состояния создания объявления
- `SearchStates` - состояния поиска
- `STATE_PROMPTS` - подсказки для пользователя
- `SEARCH_PROMPTS` - подсказки для поиска

### Клавиатуры (UI)

#### `bot/keyboards/menu.py`
**Назначение:** Главное меню и базовые клавиатуры
**Функции:**
- `main_menu_inline()` - главное меню (Выложить/Посмотреть)
- `subscription_keyboard()` - для проверки подписки

#### `bot/keyboards/rent.py`
**Назначение:** Клавиатуры для создания объявления
**Функции:**
- `district_keyboard_inline()` - выбор района (8 кнопок)
- `kb_for_state_inline()` - универсальная (Назад/Меню)
- `kb_preview_inline()` - превью с кнопками редактирования
- `kb_photos_inline()` - для загрузки фото

#### `bot/keyboards/search.py`
**Назначение:** Клавиатуры для поиска
**Функции:**
- `search_kb_for_state_inline()` - для каждого шага поиска
- `search_results_keyboard()` - навигация по результатам

### Обработчики (Handlers)

#### `bot/handlers/menu.py`
**Назначение:** Главное меню, команды, навигация
**Основные handlers:**
- `@bot.on.message(func=_is_start_trigger)` - команда /start
- `@bot.on.message(text="Поддержка")` - показать контакты
- `@bot.on.message(text=["Назад", "Меню"])` - возврат в меню
- `@bot.on.message()` - fallback handler

#### `bot/handlers/rent.py`
**Назначение:** Создание объявлений об аренде (9 шагов)
**Flow:** Район → Адрес → Этаж → Комнаты → Цена → Описание → Фото → ФИО → Телефон → Превью
**Основные handlers:**
- `@bot.on.message(text="Выложить")` - старт процесса
- `@bot.on.message(state=RentStates.DISTRICT)` - каждый шаг имеет свой handler
- `@bot.on.message(text="Отправить")` - публикация в отложенные
- `@bot.on.message(text="Район")` и др. - редактирование из превью

**Вспомогательные функции:**
- `prompt_for_state()` - показать промпт с текущим значением
- `maybe_back_to_preview()` - вернуться к превью после редактирования

#### `bot/handlers/search.py`
**Назначение:** Поиск объявлений с фильтрами
**Flow:** Район → Цена min → Цена max → Комнаты → Период → Результаты
**Основные handlers:**
- `@bot.on.message(text="Посмотреть")` - старт поиска + проверка лимитов
- `@bot.on.message(state=SearchStates.*)` - handlers для каждого фильтра
- `@bot.on.message(state=SearchStates.RESULTS)` - пагинация результатов

**Вспомогательные функции:**
- `get_search_session()` - получить сессию поиска
- `run_search_and_reply()` - выполнить поиск и показать результаты
- `send_search_results_chunk()` - отправить порцию результатов (10 штук)

### Сервисы (Business Logic)

#### `bot/services/vk_api.py`
**Назначение:** Низкоуровневая работа с VK API
**Функции:**
- `vk_api_call(method, params, token)` - универсальный вызов API
- `extract_photo_urls_from_message()` - извлечение URL фото из сообщения

#### `bot/services/post.py`
**Назначение:** Публикация постов и загрузка фото
**Функции:**
- `upload_photos_to_group(photo_urls)` - загрузить фото в сообщество (до 6 штук)
- `send_to_scheduled(text, attachments, delay)` - создать отложенный пост

**Алгоритм загрузки фото:**
1. Скачать фото по URL
2. `photos.getWallUploadServer` - получить upload_url
3. POST на upload_url - загрузить файл
4. `photos.saveWallPhoto` - сохранить в сообществе
5. Получить attachment строку `photo{owner_id}_{photo_id}`

#### `bot/services/subscription.py`
**Назначение:** Проверка подписки на сообщество
**Функции:**
- `check_subscription(user_id)` - async функция, возвращает bool

#### `bot/services/search.py`
**Назначение:** Поиск объявлений в постах сообщества
**Функции:**
- `search_posts(filters, limit, fetch_count)` - поиск с фильтрами
- `parse_post_text(text)` - парсинг текста поста в структурированные данные

**Алгоритм поиска:**
1. `wall.get` - загрузить посты сообщества
2. Фильтр по дате (если указан `recent_days`)
3. Парсинг каждого поста через `parse_post_text()`
4. Применение фильтров: район, цена min/max, комнаты
5. Сортировка по дате (старые первые)

### Утилиты (Utils)

#### `bot/utils/formatters.py`
**Назначение:** Форматирование данных для отображения
**Функции:**
- `format_price_display(value)` - "25000" → "25.000 ₽"
- `build_post_text(draft)` - черновик → текст для публикации
- `format_preview_text(draft)` - черновик → текст превью
- `format_search_result(index, item)` - форматирование результата

#### `bot/utils/validators.py`
**Назначение:** Валидация пользовательского ввода
**Функции:**
- `extract_int(text)` - извлечь число из текста ("25 000" → 25000)
- `validate_phone(text)` - (is_valid: bool, normalized: str)
- `validate_district(text)` - проверка района
- `validate_search_district(text)` - проверка района для поиска (+ "Любой")

### Хранилище (Storage)

#### `storage/storage.py`
**Назначение:** Постоянное хранилище (JSON файл)
**Класс:** `Storage`
**Методы:**
- `get_search_count(user_id)` - получить счётчик поисков
- `increment_search_count(user_id)` - увеличить счётчик
- `reset_search_count(user_id)` - сбросить счётчик (при подписке)

**Глобальный экземпляр:** `storage`

## 🔧 Типовые задачи для AI

### 1. Добавить новое поле в объявление

**Шаги:**
1. Добавить состояние в `bot/states.py` → `RentStates`
2. Добавить промпт в `STATE_PROMPTS`
3. Создать handler в `bot/handlers/rent.py`
4. Добавить валидацию в `bot/utils/validators.py` (если нужно)
5. Обновить `build_post_text()` в `bot/utils/formatters.py`
6. Добавить кнопку в `kb_preview_inline()` в `bot/keyboards/rent.py`
7. Добавить handler для редактирования

**Пример:** Добавить поле "Площадь"

```python
# 1. bot/states.py
class RentStates(BaseStateGroup):
    # ...
    AREA = "area"  # Добавить после ROOMS

STATE_PROMPTS = {
    # ...
    RentStates.AREA: "Введите площадь (м²):",
}

# 2. bot/handlers/rent.py
@bot.on.message(state=RentStates.AREA)
async def area_handler(message: Message):
    # Аналогично floor_handler или rooms_handler
    pass
```

### 2. Добавить новый фильтр в поиск

**Шаги:**
1. Добавить состояние в `bot/states.py` → `SearchStates`
2. Добавить промпт в `SEARCH_PROMPTS`
3. Создать handler в `bot/handlers/search.py`
4. Обновить `run_search_and_reply()` для передачи нового фильтра
5. Обновить `search_posts()` в `bot/services/search.py` для обработки

### 3. Изменить клавиатуру

**Файлы:**
- Главное меню → `bot/keyboards/menu.py`
- Объявления → `bot/keyboards/rent.py`
- Поиск → `bot/keyboards/search.py`

**Пример:** Добавить кнопку "История" в главное меню

```python
# bot/keyboards/menu.py
def main_menu_inline() -> str:
    kb = Keyboard(inline=True)
    kb.add(Text("Выложить"))
    kb.add(Text("Посмотреть"))
    kb.row()
    kb.add(Text("История"))  # Новая кнопка
    kb.row()
    kb.add(Text("Поддержка"), color=KeyboardButtonColor.SECONDARY)
    return kb.get_json()

# bot/handlers/menu.py
@bot.on.message(text="История")
async def history_handler(message: Message):
    # Логика
    pass
```

### 4. Добавить новый API метод VK

**Файл:** `bot/services/vk_api.py`

```python
def new_vk_method(param1, param2):
    """Описание метода."""
    resp = vk_api_call(
        "method.name",
        {
            "param1": param1,
            "param2": param2,
        }
    )
    return resp
```

### 5. Изменить форматирование

**Файл:** `bot/utils/formatters.py`

Все функции форматирования находятся здесь:
- Цены
- Тексты объявлений
- Превью
- Результаты поиска

## 🐛 Отладка

### Логирование

Каждый модуль имеет свой логгер:

```python
import logging
logger = logging.getLogger("module_name")

logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
logger.exception("Exception with traceback")
```

### Изменение уровня логирования

```python
# bot/config.py
logging.basicConfig(
    level=logging.DEBUG,  # Изменить на DEBUG для подробных логов
    format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
```

### Отслеживание состояний FSM

```python
# В любом handler
peer = message.peer_id
current_state = await bot.state_dispenser.get(peer)
logger.info(f"User {message.from_id} in state: {current_state}")
```

## 📊 Типы данных

### User Data (черновик объявления)

```python
user_data[uid] = {
    "district": str,          # "Автозаводский"
    "address": str,           # "ул. Ленина, 1"
    "floor": int,             # 5
    "rooms": int,             # 2
    "price": int,             # 25000
    "description": str,       # Любой текст
    "fio": str,               # "Иван Иванов"
    "phone": str,             # "+79123456789"
    "photo_urls": List[str],  # ["http://...", ...]
    "back_to_preview": bool,  # True если редактируем
}
```

### Search Session

```python
search_sessions[uid] = {
    "district": Optional[str],    # "Советский" или None
    "price_min": Optional[int],   # 10000 или None
    "price_max": Optional[int],   # 30000 или None
    "rooms": Optional[int],       # 2 или None
    "recent_days": Optional[int], # 7, 30 или None
    "results": List[Dict],        # Результаты поиска
    "results_offset": int,        # Текущая позиция для пагинации
}
```

### Parsed Post

```python
{
    "district": str,        # "Московский"
    "address": str,         # "ул. Победы, 10"
    "floor": str,           # "3"
    "floor_value": int,     # 3
    "rooms": str,           # "2"
    "rooms_value": int,     # 2
    "price": str,           # "20.000 ₽"
    "price_value": int,     # 20000
    "fio": str,            # "Петр Петров"
    "phone": str,          # "+79991234567"
}
```

## 🎨 Стиль кода

### Именование

- **Функции** - `snake_case` (получить_данные, build_post_text)
- **Классы** - `PascalCase` (RentStates, Storage)
- **Константы** - `UPPER_SNAKE_CASE` (GROUP_ID, MAX_SEARCHES)
- **Приватные** - `_leading_underscore` (_vk_call, _search_reset)

### Docstrings

```python
def function_name(param1: str, param2: int) -> str:
    """
    Краткое описание функции.

    Args:
        param1: Описание параметра
        param2: Описание параметра

    Returns:
        Описание возвращаемого значения
    """
    pass
```

### Импорты

```python
# Стандартная библиотека
import json
import logging
from typing import Dict, List

# Сторонние библиотеки
from vkbottle.bot import Message
from vkbottle import Keyboard

# Локальные модули
from bot import bot
from bot.config import GROUP_ID
from bot.services import vk_api_call
```

## ⚠️ Важные правила

1. **НЕ МЕНЯТЬ vkbottle** - это основной фреймворк, менять нельзя
2. **Сохранять обратную совместимость** - формат данных должен оставаться прежним
3. **Использовать существующие сервисы** - не дублировать код
4. **Добавлять логирование** - для всех важных операций
5. **Документировать изменения** - docstrings и комментарии

## 📚 Полезные ссылки

- [vkbottle документация](https://vkbottle.readthedocs.io/)
- [VK API документация](https://dev.vk.com/method)
- [README.md](README.md) - основная документация проекта
- [MIGRATION.md](MIGRATION.md) - руководство по миграции

---

**Этот документ создан для AI-ассистентов. При работе с проектом следуйте этим рекомендациям для эффективной и качественной помощи.**
