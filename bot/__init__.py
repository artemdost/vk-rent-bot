"""
Главный модуль бота.
Экспортирует экземпляр бота и глобальные переменные.
"""
from .bot_instance import bot as _bot, user_data, search_sessions

def run_forever():
    """Запускает бота в режиме polling."""
    _bot.run_polling()

# Экспортируем bot как модуль с методом run_forever
class BotModule:
    def __getattr__(self, name):
        return getattr(_bot, name)

    def run_forever(self):
        _bot.run_polling()

bot = BotModule()

__all__ = ["bot", "user_data", "search_sessions"]
