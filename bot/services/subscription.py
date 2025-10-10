"""
Сервис для проверки подписки пользователей.
"""
import logging
from bot.config import GROUP_ID, TOKEN_FOR_BOT
from bot.services.vk_api import vk_api_call

logger = logging.getLogger("subscription")


async def check_subscription(user_id: int) -> bool:
    """
    Проверяет, подписан ли пользователь на сообщество.

    Args:
        user_id: ID пользователя VK

    Returns:
        True если подписан, False если нет
    """
    if not GROUP_ID or not TOKEN_FOR_BOT:
        return True  # Если нет настроек, разрешаем всем

    try:
        resp = vk_api_call(
            "groups.isMember",
            {
                "group_id": str(GROUP_ID),
                "user_id": str(user_id),
            },
            token=TOKEN_FOR_BOT,
        )

        if "error" in resp:
            logger.warning(
                "Error checking subscription for user %s: %s", user_id, resp["error"]
            )
            return True  # В случае ошибки разрешаем

        is_member = resp.get("response", 0)
        return bool(is_member)

    except Exception as e:
        logger.exception("Exception checking subscription: %s", e)
        return True  # В случае ошибки разрешаем
