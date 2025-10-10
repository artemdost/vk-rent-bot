"""
Клавиатуры для поиска объявлений.
"""
from vkbottle import Keyboard, KeyboardButtonColor, Text
from bot.states import SearchStates


def search_kb_for_state_inline(state) -> str:
    """Клавиатура для состояния поиска."""
    if state == SearchStates.DISTRICT:
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
        kb.add(Text("Любой"), color=KeyboardButtonColor.SECONDARY)
        kb.add(Text("Меню"), color=KeyboardButtonColor.NEGATIVE)
        return kb.get_json()

    if state == SearchStates.RECENT_DAYS:
        kb = Keyboard(inline=True)
        kb.add(Text("7 дней"), color=KeyboardButtonColor.PRIMARY)
        kb.add(Text("30 дней"), color=KeyboardButtonColor.PRIMARY)
        kb.row()
        kb.add(Text("Не важно"), color=KeyboardButtonColor.SECONDARY)
        kb.row()
        kb.add(Text("Назад"), color=KeyboardButtonColor.NEGATIVE)
        kb.add(Text("Выход"), color=KeyboardButtonColor.NEGATIVE)
        return kb.get_json()

    kb = Keyboard(inline=True)
    kb.add(Text("Пропустить"), color=KeyboardButtonColor.SECONDARY)
    kb.row()
    kb.add(Text("Назад"), color=KeyboardButtonColor.NEGATIVE)
    kb.add(Text("Меню"), color=KeyboardButtonColor.NEGATIVE)
    return kb.get_json()


def search_results_keyboard(has_more: bool) -> str:
    """Клавиатура для результатов поиска."""
    kb = Keyboard(inline=True)
    if has_more:
        kb.add(Text("Ещё 10"), color=KeyboardButtonColor.PRIMARY)
        kb.row()
    kb.add(Text("Меню"), color=KeyboardButtonColor.NEGATIVE)
    return kb.get_json()
