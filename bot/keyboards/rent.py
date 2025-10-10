"""
Клавиатуры для создания объявлений об аренде.
"""
from vkbottle import Keyboard, KeyboardButtonColor, Text
from bot.states import RentStates


def district_keyboard_inline(editing: bool = False) -> str:
    """Клавиатура выбора района."""
    kb = Keyboard(inline=True)
    kb.add(Text("Автозаводский"), color=KeyboardButtonColor.PRIMARY)
    kb.add(Text("Канавинский"), color=KeyboardButtonColor.PRIMARY)
    kb.row()
    kb.add(Text("Ленинский"), color=KeyboardButtonColor.PRIMARY)
    kb.add(Text("Московский"), color=KeyboardButtonColor.PRIMARY)
    kb.row()
    kb.add(Text("Нижегородский"), color=KeyboardButtonColor.PRIMARY)
    kb.add(Text("Приокский"), color=KeyboardButtonColor.PRIMARY)
    kb.row()
    kb.add(Text("Советский"), color=KeyboardButtonColor.PRIMARY)
    kb.add(Text("Сормовский"), color=KeyboardButtonColor.PRIMARY)
    kb.row()
    kb.add(Text("Меню"), color=KeyboardButtonColor.NEGATIVE)
    if editing:
        kb.add(Text("Отмена"), color=KeyboardButtonColor.NEGATIVE)
    return kb.get_json()


def kb_for_state_inline(state, editing: bool = False) -> str:
    """Универсальная клавиатура для состояния."""
    if state == RentStates.DISTRICT:
        return district_keyboard_inline(editing=editing)

    kb = Keyboard(inline=True)
    button_title = "Отмена" if editing else "Назад"
    kb.add(Text(button_title), color=KeyboardButtonColor.NEGATIVE)
    kb.add(Text("Меню"), color=KeyboardButtonColor.NEGATIVE)
    return kb.get_json()


def kb_preview_inline(draft: dict) -> str:
    """Клавиатура предпросмотра объявления."""
    kb = Keyboard(inline=True)
    kb.add(Text("Район"))
    kb.add(Text("Телефон"))
    kb.row()
    kb.add(Text("Адрес"))
    kb.add(Text("Этаж"))
    kb.row()
    kb.add(Text("Комнаты"))
    kb.add(Text("Цена"))
    kb.row()
    kb.add(Text("Описание"))
    kb.add(Text("ФИО"))
    kb.row()
    kb.add(Text("Отправить"), color=KeyboardButtonColor.POSITIVE)
    kb.add(Text("Меню"), color=KeyboardButtonColor.NEGATIVE)
    return kb.get_json()


def kb_photos_inline(editing: bool = False) -> str:
    """Клавиатура для загрузки фото."""
    kb = Keyboard(inline=True)
    kb.add(Text("Готово"))
    kb.add(Text("Пропустить"), color=KeyboardButtonColor.SECONDARY)
    kb.row()
    cancel_title = "Отмена" if editing else "Назад"
    kb.add(Text(cancel_title), color=KeyboardButtonColor.NEGATIVE)
    kb.add(Text("Меню"), color=KeyboardButtonColor.NEGATIVE)
    return kb.get_json()
