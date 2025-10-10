"""
Обработчики для управления подписками пользователей на уведомления.
"""
import logging
import json
from vkbottle.bot import Message
from vkbottle import Keyboard, KeyboardButtonColor, Text, Callback

from bot.bot_instance import bot, search_sessions
from bot.keyboards import (
    main_menu_inline,
    subscriptions_list_keyboard,
    subscription_actions_keyboard,
)
from bot.states import SearchStates
from storage import storage

logger = logging.getLogger("subscriptions_handlers")


def format_filters(filters: dict) -> str:
    """Форматирует фильтры для отображения пользователю."""
    parts = []

    district = filters.get("district")
    if district:
        parts.append(f"Район: {district}")
    else:
        parts.append("Район: любой")

    price_min = filters.get("price_min")
    price_max = filters.get("price_max")
    if price_min and price_max:
        parts.append(f"Цена: {price_min:,} - {price_max:,} ₽".replace(",", " "))
    elif price_min:
        parts.append(f"Цена: от {price_min:,} ₽".replace(",", " "))
    elif price_max:
        parts.append(f"Цена: до {price_max:,} ₽".replace(",", " "))
    else:
        parts.append("Цена: любая")

    rooms = filters.get("rooms")
    if rooms:
        parts.append(f"Комнат: {rooms}")
    else:
        parts.append("Комнат: любое")

    recent_days = filters.get("recent_days")
    if recent_days == 7:
        parts.append("Период: 7 дней")
    elif recent_days == 30:
        parts.append("Период: 30 дней")
    else:
        parts.append("Период: любой")

    return "\n".join(parts)


@bot.on.message(text="🔔 Подписаться на уведомления")
async def subscribe_to_notifications(message: Message):
    """Обработчик подписки на уведомления по текущему поиску."""
    uid = str(message.from_id)
    user_id = message.from_id

    # Получаем параметры последнего поиска
    session = search_sessions.get(uid)
    if not session or not session.get("results"):
        await message.answer(
            "❌ Сначала выполните поиск, чтобы создать подписку на его параметры.",
            keyboard=main_menu_inline(),
        )
        return

    # Извлекаем фильтры из сессии
    filters = {
        "district": session.get("district"),
        "price_min": session.get("price_min"),
        "price_max": session.get("price_max"),
        "rooms": session.get("rooms"),
        "recent_days": session.get("recent_days"),
    }

    # Создаём подписку
    sub_id = storage.add_subscription(user_id, filters)

    filter_text = format_filters(filters)

    await message.answer(
        f"✅ Подписка создана!\n\n"
        f"Вы будете получать уведомления о новых объявлениях с параметрами:\n\n"
        f"{filter_text}\n\n"
        f"Управлять подписками можно через кнопку «Мои подписки» в главном меню.",
        keyboard=main_menu_inline(),
    )

    logger.info("User %s subscribed with ID %s", user_id, sub_id)


@bot.on.message(text="Мои подписки")
async def show_subscriptions(message: Message):
    """Показывает список подписок пользователя."""
    user_id = message.from_id
    subscriptions = storage.get_user_subscriptions(user_id)

    if not subscriptions:
        await message.answer(
            "📭 У вас пока нет активных подписок.\n\n"
            "Чтобы создать подписку:\n"
            "1. Нажмите «Посмотреть»\n"
            "2. Настройте параметры поиска\n"
            "3. Нажмите «🔔 Подписаться на уведомления»",
            keyboard=main_menu_inline(),
        )
        return

    # Формируем сообщение со списком подписок
    text = f"📬 Ваши подписки ({len(subscriptions)}):\n\n"

    for idx, sub in enumerate(subscriptions, 1):
        status = "✅ Активна" if sub.get("enabled", True) else "⏸ Отключена"
        filter_text = format_filters(sub.get("filters", {}))

        text += f"{idx}. {status}\n"
        text += f"ID: {sub['id']}\n"
        text += f"{filter_text}\n\n"

    # Создаём клавиатуру с кнопками для каждой подписки
    kb = Keyboard(inline=True)

    for idx, sub in enumerate(subscriptions, 1):
        is_enabled = sub.get("enabled", True)
        icon = "✅" if is_enabled else "⏸"
        kb.add(Text(f"{icon} Подписка #{idx}"))
        if idx % 2 == 0:
            kb.row()

    if len(subscriptions) % 2 != 0:
        kb.row()

    kb.add(Text("Меню"), color=KeyboardButtonColor.NEGATIVE)

    await message.answer(text, keyboard=kb.get_json())


@bot.on.message()
async def handle_subscription_action(message: Message):
    """Обработчик действий с подписками."""
    text = (message.text or "").strip()

    # Проверяем, это кнопка подписки
    if not text.startswith("✅ Подписка #") and not text.startswith("⏸ Подписка #"):
        return

    user_id = message.from_id
    uid = str(user_id)
    subscriptions = storage.get_user_subscriptions(user_id)

    if not subscriptions:
        await message.answer(
            "❌ Подписка не найдена.",
            keyboard=main_menu_inline(),
        )
        return

    # Извлекаем номер подписки
    try:
        sub_num = int(text.split("#")[1])
        if sub_num < 1 or sub_num > len(subscriptions):
            raise ValueError()
        sub = subscriptions[sub_num - 1]
    except (ValueError, IndexError):
        await message.answer(
            "❌ Неверный номер подписки.",
            keyboard=main_menu_inline(),
        )
        return

    # Сохраняем ID подписки в сессии для дальнейших действий
    from bot.bot_instance import search_sessions
    if uid not in search_sessions:
        search_sessions[uid] = {}
    search_sessions[uid]["current_subscription_id"] = sub["id"]

    # Показываем детали подписки с действиями
    is_enabled = sub.get("enabled", True)
    status = "✅ Активна" if is_enabled else "⏸ Отключена"
    filter_text = format_filters(sub.get("filters", {}))

    response_text = (
        f"📋 Подписка #{sub_num}\n"
        f"Статус: {status}\n"
        f"ID: {sub['id']}\n\n"
        f"{filter_text}\n\n"
        f"Выберите действие:"
    )

    # Создаём клавиатуру с действиями
    kb = Keyboard(inline=True)

    if is_enabled:
        kb.add(Text("⏸ Отключить"))
    else:
        kb.add(Text("▶️ Включить"), color=KeyboardButtonColor.POSITIVE)

    kb.add(Text("🗑 Удалить"), color=KeyboardButtonColor.NEGATIVE)
    kb.row()
    kb.add(Text("⬅️ К подпискам"), color=KeyboardButtonColor.PRIMARY)

    await message.answer(response_text, keyboard=kb.get_json())


@bot.on.message(text=["⏸ Отключить", "▶️ Включить"])
async def toggle_subscription(message: Message):
    """Переключает статус подписки."""
    user_id = message.from_id
    uid = str(user_id)

    # Получаем ID подписки из сессии
    from bot.bot_instance import search_sessions
    session = search_sessions.get(uid, {})
    sub_id = session.get("current_subscription_id")

    if not sub_id:
        await message.answer(
            "❌ Подписка не найдена. Выберите подписку из списка.",
            keyboard=main_menu_inline(),
        )
        return

    new_status = storage.toggle_subscription(user_id, sub_id)

    status_text = "включена" if new_status else "отключена"

    await message.answer(
        f"✅ Подписка {status_text}.",
    )

    # Перенаправляем обратно к списку подписок
    await show_subscriptions(message)


@bot.on.message(text="🗑 Удалить")
async def delete_subscription(message: Message):
    """Удаляет подписку."""
    user_id = message.from_id
    uid = str(user_id)

    # Получаем ID подписки из сессии
    from bot.bot_instance import search_sessions
    session = search_sessions.get(uid, {})
    sub_id = session.get("current_subscription_id")

    if not sub_id:
        await message.answer(
            "❌ Подписка не найдена. Выберите подписку из списка.",
            keyboard=main_menu_inline(),
        )
        return

    success = storage.delete_subscription(user_id, sub_id)

    if success:
        await message.answer(
            "✅ Подписка удалена.",
        )
        logger.info("User %s deleted subscription %s", user_id, sub_id)
        # Очищаем сессию
        if "current_subscription_id" in session:
            del session["current_subscription_id"]
        # Показываем обновленный список
        await show_subscriptions(message)
    else:
        await message.answer(
            "❌ Не удалось удалить подписку.",
            keyboard=main_menu_inline(),
        )


@bot.on.message(text="⬅️ К подпискам")
async def back_to_subscriptions(message: Message):
    """Возврат к списку подписок."""
    await show_subscriptions(message)
