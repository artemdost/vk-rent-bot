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

# Импортируем функцию для мониторинга новых постов
from bot.services.notifications import check_new_posts_and_notify


async def notification_loop():
    """
    Фоновая задача для проверки новых постов.
    Работает параллельно с Long Poll.
    """
    LOG.info("Notification loop started - checking new posts every 1 minute")

    while True:
        try:
            count = await check_new_posts_and_notify()
            if count > 0:
                LOG.info("Sent %d notifications", count)
        except Exception as e:
            LOG.exception("Error in notification loop: %s", e)

        # Проверяем каждую минуту
        await asyncio.sleep(60)


async def start_notification_loop():
    """Запускает фоновую задачу для проверки новых постов."""
    asyncio.create_task(notification_loop())


# Добавляем задачу в on_startup
bot_instance.bot.loop_wrapper.on_startup.append(start_notification_loop())


if __name__ == "__main__":
    try:
        LOG.info("Bot starting...")
        LOG.info("Wall post notifications enabled via polling (every 60 seconds)")
        bot_instance.bot.run_forever()
    except KeyboardInterrupt:
        LOG.info("Bot stopped by user")
    except Exception as e:
        LOG.exception("Bot crashed: %s", e)
        raise
