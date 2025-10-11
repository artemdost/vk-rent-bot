"""
Клавиатуры главного меню.
"""
from vkbottle import Keyboard, KeyboardButtonColor, Text
from bot.constants import Button


def main_menu_inline() -> str:
    """Главное меню бота."""
    kb = Keyboard(inline=True)
    kb.add(Text(Button.POST_AD))
    kb.add(Text(Button.VIEW_ADS))
    kb.row()
    kb.add(Text(Button.MY_SUBSCRIPTIONS), color=KeyboardButtonColor.PRIMARY)
    kb.row()
    kb.add(Text(Button.CHECK_CONTRACT), color=KeyboardButtonColor.POSITIVE)
    kb.row()
    kb.add(Text(Button.SUPPORT), color=KeyboardButtonColor.SECONDARY)
    return kb.get_json()


def subscription_keyboard() -> str:
    """Клавиатура с кнопкой подписки."""
    kb = Keyboard(inline=True)
    kb.add(Text(Button.CHECK_SUBSCRIPTION), color=KeyboardButtonColor.POSITIVE)
    kb.row()
    kb.add(Text(Button.MENU), color=KeyboardButtonColor.NEGATIVE)
    return kb.get_json()
