"""
Точка входа для VK бота аренды квартир.
Запуск: python main.py
"""
import asyncio

# Импортируем bot_instance напрямую чтобы получить экземпляр бота
from bot import bot_instance
from bot.config import LOG

# Импортируем хендлеры для регистрации
import bot.handlers

# Импортируем notification loop
from bot.services.notifications import notification_loop


async def start_notification_loop():
    """Запускает фоновую задачу для проверки новых постов."""
    LOG.info("Starting notification loop...")
    asyncio.create_task(notification_loop())


# Добавляем задачу в on_startup
bot_instance.bot.loop_wrapper.on_startup.append(start_notification_loop())


if __name__ == "__main__":
    try:
        LOG.info("Bot starting...")
        bot_instance.bot.run_forever()
    except KeyboardInterrupt:
        LOG.info("Bot stopped by user")
    except Exception as e:
        LOG.exception("Bot crashed: %s", e)
        raise
