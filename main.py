"""
Точка входа для VK бота аренды квартир.
Запуск: python main.py
"""

# Импортируем bot_instance напрямую чтобы получить экземпляр бота
from bot import bot_instance
from bot.config import LOG

# Импортируем хендлеры для регистрации (включая wall_events)
import bot.handlers


if __name__ == "__main__":
    try:
        LOG.info("Bot starting...")
        LOG.info("Wall post notifications enabled via Callback API")
        bot_instance.bot.run_forever()
    except KeyboardInterrupt:
        LOG.info("Bot stopped by user")
    except Exception as e:
        LOG.exception("Bot crashed: %s", e)
        raise
