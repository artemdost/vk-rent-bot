"""
Константы для текстов кнопок и сообщений бота.
Все тексты вынесены в один файл для предотвращения опечаток и упрощения изменений.
"""

# ============================================================================
# ТЕКСТЫ КНОПОК ГЛАВНОГО МЕНЮ
# ============================================================================

class Button:
    """Тексты всех кнопок в боте."""

    # Главное меню
    MENU = "Меню"
    POST_AD = "Выложить"
    VIEW_ADS = "Посмотреть"
    MY_SUBSCRIPTIONS = "Мои подписки"
    CHECK_CONTRACT = "🤖 Проверить договор"
    SUPPORT = "Поддержка"
    CHECK_SUBSCRIPTION = "Проверить подписку"

    # Навигация
    BACK = "Назад"
    CANCEL = "Отмена"
    EXIT = "Выход"
    SKIP = "Пропустить"
    DONE = "Готово"

    # Подписки
    SUBSCRIBE = "🔔 Подписаться на уведомления"
    BACK_TO_SUBSCRIPTIONS = "⬅️ К подпискам"
    TOGGLE_DISABLE = "⏸ Отключить"
    TOGGLE_ENABLE = "▶️ Включить"
    DELETE = "🗑 Удалить"
    CONFIRM_DELETE = "✅ Да, удалить"

    # Поиск
    SHOW_MORE = "Ещё 10"

    # Публикация
    SEND = "Отправить"

    # Поля объявления
    FIELD_DISTRICT = "Район"
    FIELD_ADDRESS = "Адрес"
    FIELD_FLOOR = "Этаж"
    FIELD_ROOMS = "Комнаты"
    FIELD_PRICE = "Цена"
    FIELD_DESCRIPTION = "Описание"
    FIELD_FULLNAME = "ФИО"
    FIELD_PHONE = "Телефон"

    # Районы Нижнего Новгорода
    DISTRICT_AVTOZAVODSKY = "Автозаводский"
    DISTRICT_KANAVINSKY = "Канавинский"
    DISTRICT_LENINSKY = "Ленинский"
    DISTRICT_MOSKOVSKY = "Московский"
    DISTRICT_NIZHEGORODSKY = "Нижегородский"
    DISTRICT_PRIOKSKY = "Приокский"
    DISTRICT_SOVETSKY = "Советский"
    DISTRICT_SORMOVSKY = "Сормовский"
    DISTRICT_ANY = "Любой"

    # Периоды для поиска
    PERIOD_7_DAYS = "7 дней"
    PERIOD_30_DAYS = "30 дней"
    PERIOD_ANY = "Не важно"


# Список всех районов для использования в коде
DISTRICTS = [
    Button.DISTRICT_AVTOZAVODSKY,
    Button.DISTRICT_KANAVINSKY,
    Button.DISTRICT_LENINSKY,
    Button.DISTRICT_MOSKOVSKY,
    Button.DISTRICT_NIZHEGORODSKY,
    Button.DISTRICT_PRIOKSKY,
    Button.DISTRICT_SOVETSKY,
    Button.DISTRICT_SORMOVSKY,
]


# ============================================================================
# СООБЩЕНИЯ ПОЛЬЗОВАТЕЛЮ
# ============================================================================

class Message:
    """Шаблоны сообщений для пользователя."""

    # Ошибки
    ERROR_NO_SEARCH = "❌ Сначала выполните поиск, чтобы создать подписку на его параметры."
    ERROR_SUBSCRIPTION_NOT_FOUND = "❌ Подписка не найдена. Выберите подписку из списка."
    ERROR_INVALID_SUBSCRIPTION_NUMBER = "❌ Неверный номер подписки."
    ERROR_DELETE_FAILED = "❌ Не удалось удалить подписку."

    # Подписки
    SUBSCRIPTION_CREATED = "✅ Подписка создана!"
    SUBSCRIPTION_DUPLICATE = "⚠️ У вас уже есть активная подписка с такими же параметрами.\n\nВы можете управлять своими подписками через кнопку «Мои подписки»."
    SUBSCRIPTION_ENABLED = "✅ Подписка включена."
    SUBSCRIPTION_DISABLED = "✅ Подписка отключена."
    SUBSCRIPTION_DELETED = "✅ Подписка удалена."
    SUBSCRIPTION_DELETE_CONFIRM = "⚠️ Вы уверены, что хотите удалить подписку?\n\nЭто действие нельзя отменить."
    SUBSCRIPTION_DELETE_CANCELLED = "Удаление отменено."

    NO_SUBSCRIPTIONS = (
        "📭 У вас пока нет активных подписок.\n\n"
        "Чтобы создать подписку:\n"
        "1. Нажмите «Посмотреть»\n"
        "2. Настройте параметры поиска\n"
        "3. Нажмите «🔔 Подписаться на уведомления»"
    )

    # Уведомления
    NEW_AD_NOTIFICATION = "🔔 Новое объявление!\n\nНайдено объявление по вашей подписке:\n{filters}\n\nСмотрите объявление ниже:"

    # Информационные
    SUBSCRIPTION_INFO = "Вы будете получать уведомления о новых объявлениях с параметрами:\n\n{filters}\n\nУправлять подписками можно через кнопку «Мои подписки»."

    # Проверка договора
    CONTRACT_ANALYZING = "🔍 Анализирую договор..."
    CONTRACT_ERROR_NO_FILES = "❌ Не удалось получить файлы. Пожалуйста, прикрепите документ."
    CONTRACT_ERROR_UNSUPPORTED = "❌ Неподдерживаемый формат файла. Поддерживаются: PDF, DOCX, TXT, JPG, PNG."
    CONTRACT_ERROR_DOWNLOAD = "❌ Не удалось загрузить файл. Попробуйте еще раз."
    CONTRACT_ERROR_PARSE = "❌ Не удалось прочитать содержимое файла."
    CONTRACT_ERROR_ANALYSIS = "❌ Произошла ошибка при анализе договора. Попробуйте позже."
    CONTRACT_TOO_LARGE = "❌ Файл слишком большой. Максимальный размер: 10 МБ."
    CONTRACT_RECEIVED = "📥 Получен {file_type} файл. Начинаю анализ..."

    CONTRACT_RESULT_HEADER = "📋 РЕЗУЛЬТАТЫ ПРОВЕРКИ ДОГОВОРА\n" + "=" * 30
    CONTRACT_HIGH_RISK = "🔴 ВЫСОКИЙ РИСК"
    CONTRACT_MEDIUM_RISK = "🟡 СРЕДНИЙ РИСК"
    CONTRACT_LOW_RISK = "🟢 НИЗКИЙ РИСК"

    CONTRACT_BACK_TO_MENU = "Для проверки другого договора нажмите «Проверить договор» в главном меню."


# ============================================================================
# ФОРМАТИРОВАНИЕ
# ============================================================================

class Format:
    """Константы для форматирования данных."""

    # Статусы подписок
    SUBSCRIPTION_ACTIVE = "✅ Активна"
    SUBSCRIPTION_PAUSED = "⏸ Отключена"

    # Префиксы кнопок подписок
    SUBSCRIPTION_BUTTON_ACTIVE_PREFIX = "✅ Подписка #"
    SUBSCRIPTION_BUTTON_PAUSED_PREFIX = "⏸ Подписка #"

    # Форматы фильтров
    FILTER_DISTRICT = "Район: {district}"
    FILTER_DISTRICT_ANY = "Район: любой"
    FILTER_PRICE_RANGE = "Цена: {min} - {max} ₽"
    FILTER_PRICE_MIN = "Цена: от {min} ₽"
    FILTER_PRICE_MAX = "Цена: до {max} ₽"
    FILTER_PRICE_ANY = "Цена: любая"
    FILTER_ROOMS = "Комнат: {rooms}"
    FILTER_ROOMS_ANY = "Комнат: любое"
