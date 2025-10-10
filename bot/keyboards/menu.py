"""
Клавиатуры главного меню.
"""
from vkbottle import Keyboard, KeyboardButtonColor, Text


def main_menu_inline() -> str:
    """Главное меню бота."""
    kb = Keyboard(inline=True)
    kb.add(Text("Выложить"))
    kb.add(Text("Посмотреть"))
    kb.row()
    kb.add(Text("Мои подписки"), color=KeyboardButtonColor.PRIMARY)
    kb.row()
    kb.add(Text("Поддержка"), color=KeyboardButtonColor.SECONDARY)
    return kb.get_json()


def subscription_keyboard() -> str:
    """Клавиатура с кнопкой подписки."""
    kb = Keyboard(inline=True)
    kb.add(Text("Проверить подписку"), color=KeyboardButtonColor.POSITIVE)
    kb.row()
    kb.add(Text("Меню"), color=KeyboardButtonColor.NEGATIVE)
    return kb.get_json()
