"""
Обработчики событий публикации постов на стене группы.
Автоматически проверяет новые посты на соответствие подпискам и отправляет уведомления.
"""
import logging
import asyncio
from vkbottle.bot import Message
from vkbottle import GroupEventType

from bot.bot_instance import bot
from bot.services.search import parse_post_text
from bot.services.notifications import match_post_with_filters, send_notification
from storage import storage

logger = logging.getLogger("wall_events")


@bot.on.raw_event(GroupEventType.WALL_POST_NEW, dataclass=dict)
async def wall_post_new_handler(event: dict):
    """
    Обработчик события публикации нового поста на стене.
    Срабатывает автоматически когда в группе публикуется новый пост.
    """
    try:
        obj = event.get("object", {})
        post_id = obj.get("id")
        text = obj.get("text", "")

        logger.info("New wall post detected: ID=%s", post_id)

        # Парсим пост
        parsed = parse_post_text(text)
        if not parsed:
            logger.info("Post %s does not contain rental ad data, skipping", post_id)
            return

        logger.info("Post %s parsed successfully: %s", post_id, parsed)

        # Получаем все активные подписки
        active_subs = storage.get_all_active_subscriptions()
        if not active_subs:
            logger.info("No active subscriptions, skipping notifications")
            return

        notifications_sent = 0

        # Проверяем каждую подписку
        for user_id, subscription in active_subs:
            filters = subscription.get("filters", {})
            sub_id = subscription.get("id")
            last_notified = subscription.get("last_notified_post_id")

            # Пропускаем если этот пост уже был отправлен этой подписке
            if last_notified is not None and post_id <= last_notified:
                continue

            # Проверяем соответствие фильтрам
            if match_post_with_filters(parsed, filters):
                # Формируем объект поста для отправки
                post_obj = {
                    "id": post_id,
                    "text": text,
                }

                success = await send_notification(user_id, post_obj, filters)
                if success:
                    notifications_sent += 1
                    # Обновляем ID последнего отправленного поста для этой подписки
                    storage.update_subscription_last_notified_post(user_id, sub_id, post_id)
                    logger.info(
                        "Sent notification to user %s for post %s (subscription %s)",
                        user_id,
                        post_id,
                        sub_id,
                    )

                # Небольшая задержка между отправками
                await asyncio.sleep(0.5)

        logger.info("Processed post %s: sent %d notifications", post_id, notifications_sent)

    except Exception as e:
        logger.exception("Error processing wall_post_new event: %s", e)
