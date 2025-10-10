"""
Сервис для работы с уведомлениями о новых объявлениях.
Проверяет новые посты и отправляет уведомления подписчикам.
"""
import logging
import asyncio
import random
from typing import Dict, Any, List, Optional

from bot.config import GROUP_ID, TOKEN_FOR_BOT
from bot.services.vk_api import vk_api_call
from bot.services.search import parse_post_text
from storage import storage

logger = logging.getLogger("notifications")


def _random_id() -> int:
    """Генерирует случайный ID для сообщения."""
    return random.randint(-2_147_483_648, 2_147_483_647)


def match_post_with_filters(parsed_post: Dict[str, Any], filters: Dict[str, Any]) -> bool:
    """
    Проверяет, соответствует ли пост фильтрам подписки.

    Args:
        parsed_post: Распарсенные данные поста
        filters: Фильтры подписки

    Returns:
        True если пост подходит под фильтры
    """
    # Фильтр по району
    district_filter = filters.get("district")
    if district_filter:
        district = parsed_post.get("district")
        if not district or district.lower() != district_filter.lower():
            return False

    # Фильтр по цене
    price_value = parsed_post.get("price_value")
    price_min = filters.get("price_min")
    price_max = filters.get("price_max")

    if price_min is not None:
        if price_value is None or price_value < price_min:
            return False
    if price_max is not None:
        if price_value is None or price_value > price_max:
            return False

    # Фильтр по комнатам
    rooms_value = parsed_post.get("rooms_value")
    rooms_filter = filters.get("rooms")
    if rooms_filter is not None:
        if rooms_value is None or rooms_value != rooms_filter:
            return False

    return True


async def send_notification(user_id: int, post: Dict[str, Any], filters: Dict[str, Any]) -> bool:
    """
    Отправляет уведомление пользователю о новом объявлении.

    Args:
        user_id: ID пользователя
        post: Данные поста
        filters: Фильтры подписки (для формирования текста)

    Returns:
        True если уведомление отправлено успешно
    """
    try:
        post_id = post.get("id")
        owner_id = -abs(int(GROUP_ID))
        attachment = f"wall{owner_id}_{post_id}" if post_id else None

        # Формируем текст уведомления
        filter_parts = []
        if filters.get("district"):
            filter_parts.append(f"Район: {filters['district']}")
        if filters.get("price_min"):
            filter_parts.append(f"Цена от: {filters['price_min']}")
        if filters.get("price_max"):
            filter_parts.append(f"Цена до: {filters['price_max']}")
        if filters.get("rooms"):
            filter_parts.append(f"Комнат: {filters['rooms']}")

        filter_text = ", ".join(filter_parts) if filter_parts else "все параметры"

        message = (
            f"🔔 Новое объявление!\n\n"
            f"Найдено объявление по вашей подписке:\n"
            f"{filter_text}\n\n"
            f"Смотрите объявление ниже:"
        )

        # Импортируем клавиатуру меню
        from bot.keyboards import main_menu_inline

        # Используем синхронный вызов через vk_api_call
        response = vk_api_call(
            "messages.send",
            {
                "user_id": user_id,
                "random_id": _random_id(),
                "message": message,
                "attachment": attachment,
                "keyboard": main_menu_inline(),  # Добавляем клавиатуру
            },
            token=TOKEN_FOR_BOT,
        )

        if "error" in response:
            logger.warning(
                "Failed to send notification to user %s: %s",
                user_id,
                response["error"].get("error_msg"),
            )
            return False

        return True

    except Exception as e:
        logger.exception("Error sending notification to user %s: %s", user_id, e)
        return False


async def check_new_posts_and_notify() -> int:
    """
    Проверяет новые посты и отправляет уведомления подписчикам.

    Returns:
        Количество отправленных уведомлений
    """
    from bot.config import USER_TOKEN, UPLOAD_TOKEN

    if not GROUP_ID:
        logger.warning("GROUP_ID not configured, skipping notification check")
        return 0

    # Используем USER_TOKEN или UPLOAD_TOKEN для wall.get
    token_for_wall = USER_TOKEN or UPLOAD_TOKEN
    if not token_for_wall:
        logger.warning("USER_TOKEN or UPLOAD_TOKEN not configured, skipping notification check")
        return 0

    try:
        owner_id = -abs(int(GROUP_ID))
        last_checked_id = storage.get_last_checked_post_id()

        # Получаем последние посты
        response = vk_api_call(
            "wall.get",
            {
                "owner_id": owner_id,
                "count": 10,  # Проверяем последние 10 постов
                "offset": 0,
            },
            token=token_for_wall,  # Используем user token вместо group token
        )

        if "error" in response:
            logger.warning("Failed to fetch posts: %s", response["error"].get("error_msg"))
            return 0

        items = response.get("response", {}).get("items", [])
        if not items:
            return 0

        # Определяем новые посты
        new_posts = []
        latest_post_id = items[0].get("id") if items else last_checked_id

        for post in items:
            post_id = post.get("id")
            if last_checked_id is None or post_id > last_checked_id:
                new_posts.append(post)

        if not new_posts:
            return 0

        logger.info("Found %d new posts", len(new_posts))

        # Получаем все активные подписки
        active_subs = storage.get_all_active_subscriptions()
        if not active_subs:
            # Обновляем ID последнего проверенного поста даже если нет подписок
            if latest_post_id:
                storage.set_last_checked_post_id(latest_post_id)
            return 0

        notifications_sent = 0

        # Проверяем каждый новый пост
        for post in new_posts:
            text = post.get("text", "")
            parsed = parse_post_text(text)

            if not parsed:
                continue

            # Проверяем каждую подписку
            for user_id, subscription in active_subs:
                filters = subscription.get("filters", {})

                if match_post_with_filters(parsed, filters):
                    success = await send_notification(user_id, post, filters)
                    if success:
                        notifications_sent += 1
                        logger.info(
                            "Sent notification to user %s for post %s",
                            user_id,
                            post.get("id"),
                        )

                    # Небольшая задержка между отправками
                    await asyncio.sleep(0.5)

        # Обновляем ID последнего проверенного поста
        if latest_post_id:
            storage.set_last_checked_post_id(latest_post_id)

        logger.info("Sent %d notifications", notifications_sent)
        return notifications_sent

    except Exception as e:
        logger.exception("Error checking new posts: %s", e)
        return 0


async def notification_loop():
    """
    Бесконечный цикл проверки новых постов.
    Проверяет каждые 5 минут.
    """
    logger.info("Notification loop started")

    while True:
        try:
            await check_new_posts_and_notify()
        except Exception as e:
            logger.exception("Error in notification loop: %s", e)

        # Ждём 5 минут перед следующей проверкой
        await asyncio.sleep(300)
