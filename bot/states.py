"""
Состояния FSM (Finite State Machine) для бота.
Определяет все возможные состояния диалогов.
"""
from vkbottle import BaseStateGroup


class RentStates(BaseStateGroup):
    """Состояния для создания объявления об аренде."""
    DISTRICT = "district"
    ADDRESS = "address"
    FLOOR = "floor"
    ROOMS = "rooms"
    PRICE = "price"
    DESCRIPTION = "description"
    FIO = "fio"
    PHONE = "phone"
    PHOTOS = "photos"
    PREVIEW = "preview"


class SearchStates(BaseStateGroup):
    """Состояния для поиска объявлений."""
    DISTRICT = "search_district"
    PRICE_MIN = "search_price_min"
    PRICE_MAX = "search_price_max"
    ROOMS = "search_rooms"
    RECENT_DAYS = "search_recent_days"
    RESULTS = "search_results"


class ContractStates(BaseStateGroup):
    """Состояния для проверки договора."""
    UPLOAD = "contract_upload"
    PROCESSING = "contract_processing"
    RESULTS = "contract_results"


# Подсказки для состояний аренды
STATE_PROMPTS = {
    RentStates.DISTRICT: "Выберите район:",
    RentStates.ADDRESS: "Введите адрес:",
    RentStates.FLOOR: "Введите этаж (цифрами):",
    RentStates.ROOMS: "Введите количество комнат (цифрами):",
    RentStates.PHOTOS: "Прикрепите фото (до 6 штук).",
    RentStates.PRICE: "Введите цену (цифрами):",
    RentStates.DESCRIPTION: "Введите описание квартиры:",
    RentStates.FIO: "Введите ФИО (как вы хотите, чтобы с вами связались):",
    RentStates.PHONE: "Введите номер телефона (пример: +7 912 345-67-89 или 89123456789):",
}

# Подсказки для состояний поиска
SEARCH_PROMPTS = {
    SearchStates.DISTRICT: "Выберите район или нажмите «Любой»:",
    SearchStates.PRICE_MIN: "Укажите минимальную цену",
    SearchStates.PRICE_MAX: "Укажите максимальную цену",
    SearchStates.ROOMS: "Сколько комнат вас интересует?",
    SearchStates.RECENT_DAYS: "Показать объявления за 7 дней, за 30 дней или без ограничения?",
}

# Подсказки для состояний проверки договора
CONTRACT_PROMPTS = {
    ContractStates.UPLOAD: (
        "📄 Отправьте договор для проверки\n\n"
        "Поддерживаемые форматы:\n"
        "• PDF документы\n"
        "• Фотографии (JPG, PNG)\n"
        "• Текстовые файлы (TXT)\n"
        "• Word документы (DOCX)\n\n"
        "Можно отправить несколько файлов или фотографий сразу."
    ),
    ContractStates.PROCESSING: "⏳ Анализирую договор...\n\nЭто может занять несколько секунд.",
    ContractStates.RESULTS: "Результаты проверки готовы.",
}
