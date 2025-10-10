"""
Клавиатуры для поиска объявлений.
"""
from vkbottle import Keyboard, KeyboardButtonColor, Text
from bot.states import SearchStates
from bot.constants import Button


def search_kb_for_state_inline(state) -> str:
    """Клавиатура для состояния поиска."""
    if state == SearchStates.DISTRICT:
        kb = Keyboard(inline=True)
        kb.add(Text(Button.DISTRICT_AVTOZAVODSKY), color=KeyboardButtonColor.PRIMARY)
        kb.add(Text(Button.DISTRICT_KANAVINSKY), color=KeyboardButtonColor.PRIMARY)
        kb.row()
        kb.add(Text(Button.DISTRICT_LENINSKY), color=KeyboardButtonColor.PRIMARY)
        kb.add(Text(Button.DISTRICT_MOSKOVSKY), color=KeyboardButtonColor.PRIMARY)
        kb.row()
        kb.add(Text(Button.DISTRICT_NIZHEGORODSKY), color=KeyboardButtonColor.PRIMARY)
        kb.add(Text(Button.DISTRICT_PRIOKSKY), color=KeyboardButtonColor.PRIMARY)
        kb.row()
        kb.add(Text(Button.DISTRICT_SOVETSKY), color=KeyboardButtonColor.PRIMARY)
        kb.add(Text(Button.DISTRICT_SORMOVSKY), color=KeyboardButtonColor.PRIMARY)
        kb.row()
        kb.add(Text(Button.DISTRICT_ANY), color=KeyboardButtonColor.SECONDARY)
        kb.add(Text(Button.MENU), color=KeyboardButtonColor.NEGATIVE)
        return kb.get_json()

    if state == SearchStates.RECENT_DAYS:
        kb = Keyboard(inline=True)
        kb.add(Text(Button.PERIOD_7_DAYS), color=KeyboardButtonColor.PRIMARY)
        kb.add(Text(Button.PERIOD_30_DAYS), color=KeyboardButtonColor.PRIMARY)
        kb.row()
        kb.add(Text(Button.PERIOD_ANY), color=KeyboardButtonColor.SECONDARY)
        kb.row()
        kb.add(Text(Button.BACK), color=KeyboardButtonColor.NEGATIVE)
        kb.add(Text(Button.EXIT), color=KeyboardButtonColor.NEGATIVE)
        return kb.get_json()

    kb = Keyboard(inline=True)
    kb.add(Text(Button.SKIP), color=KeyboardButtonColor.SECONDARY)
    kb.row()
    kb.add(Text(Button.BACK), color=KeyboardButtonColor.NEGATIVE)
    kb.add(Text(Button.MENU), color=KeyboardButtonColor.NEGATIVE)
    return kb.get_json()


def search_results_keyboard(has_more: bool, show_subscribe: bool = False) -> str:
    """Клавиатура для результатов поиска."""
    kb = Keyboard(inline=True)
    if has_more:
        kb.add(Text(Button.SHOW_MORE), color=KeyboardButtonColor.PRIMARY)
        kb.row()
    if show_subscribe:
        kb.add(Text(Button.SUBSCRIBE), color=KeyboardButtonColor.POSITIVE)
        kb.row()
    kb.add(Text(Button.MENU), color=KeyboardButtonColor.NEGATIVE)
    return kb.get_json()


def subscriptions_list_keyboard() -> str:
    """Клавиатура для списка подписок."""
    kb = Keyboard(inline=True)
    kb.add(Text(Button.MENU), color=KeyboardButtonColor.NEGATIVE)
    return kb.get_json()


def subscription_actions_keyboard(is_enabled: bool) -> str:
    """Клавиатура для действий с подпиской."""
    kb = Keyboard(inline=True)

    if is_enabled:
        kb.add(Text(Button.TOGGLE_DISABLE), color=KeyboardButtonColor.SECONDARY)
    else:
        kb.add(Text(Button.TOGGLE_ENABLE), color=KeyboardButtonColor.POSITIVE)

    kb.add(Text(Button.DELETE), color=KeyboardButtonColor.NEGATIVE)
    kb.row()
    kb.add(Text(Button.BACK), color=KeyboardButtonColor.PRIMARY)
    return kb.get_json()
