"""
Обработчики для управления подписками пользователей на уведомления.
"""
import logging
import json
from vkbottle.bot import Message
from vkbottle import Keyboard, KeyboardButtonColor, Text, Callback

from bot.bot_instance import bot, search_sessions
from bot.constants import Button, Message as Msg, Format
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
        parts.append(Format.FILTER_DISTRICT.format(district=district))
    else:
        parts.append(Format.FILTER_DISTRICT_ANY)

    price_min = filters.get("price_min")
    price_max = filters.get("price_max")
    if price_min and price_max:
        parts.append(Format.FILTER_PRICE_RANGE.format(
            min=f"{price_min:,}".replace(",", " "),
            max=f"{price_max:,}".replace(",", " ")
        ))
    elif price_min:
        parts.append(Format.FILTER_PRICE_MIN.format(min=f"{price_min:,}".replace(",", " ")))
    elif price_max:
        parts.append(Format.FILTER_PRICE_MAX.format(max=f"{price_max:,}".replace(",", " ")))
    else:
        parts.append(Format.FILTER_PRICE_ANY)

    rooms = filters.get("rooms")
    if rooms:
        parts.append(Format.FILTER_ROOMS.format(rooms=rooms))
    else:
        parts.append(Format.FILTER_ROOMS_ANY)

    return "\n".join(parts)


@bot.on.message(text=Button.SUBSCRIBE)
async def subscribe_to_notifications(message: Message):
    """Обработчик подписки на уведомления по текущему поиску."""
    uid = str(message.from_id)
    user_id = message.from_id

    # Получаем параметры последнего поиска
    session = search_sessions.get(uid)
    if not session or not session.get("results"):
        await message.answer(
            Msg.ERROR_NO_SEARCH,
            keyboard=main_menu_inline(),
        )
        return

    # Извлекаем фильтры из сессии (без периода - подписки работают на все новые объявления)
    filters = {
        "district": session.get("district"),
        "price_min": session.get("price_min"),
        "price_max": session.get("price_max"),
        "rooms": session.get("rooms"),
    }

    # Проверяем на дубликаты
    existing_subs = storage.get_user_subscriptions(user_id)
    for existing_sub in existing_subs:
        if existing_sub.get("filters") == filters:
            # Создаём клавиатуру для дублирующей подписки
            kb = Keyboard(inline=True)
            kb.add(Text(Button.MY_SUBSCRIPTIONS), color=KeyboardButtonColor.PRIMARY)
            kb.add(Text(Button.MENU), color=KeyboardButtonColor.SECONDARY)

            await message.answer(
                Msg.SUBSCRIPTION_DUPLICATE,
                keyboard=kb.get_json(),
            )
            return

    # Создаём подписку
    sub_id = storage.add_subscription(user_id, filters)

    filter_text = format_filters(filters)

    # Создаём клавиатуру с быстрым доступом к подпискам
    kb = Keyboard(inline=True)
    kb.add(Text(Button.MY_SUBSCRIPTIONS), color=KeyboardButtonColor.PRIMARY)
    kb.add(Text(Button.MENU), color=KeyboardButtonColor.SECONDARY)

    await message.answer(
        f"{Msg.SUBSCRIPTION_CREATED}\n\n{Msg.SUBSCRIPTION_INFO.format(filters=filter_text)}",
        keyboard=kb.get_json(),
    )

    logger.info("User %s subscribed with ID %s", user_id, sub_id)


@bot.on.message(text=Button.MY_SUBSCRIPTIONS)
async def show_subscriptions(message: Message):
    """Показывает список подписок пользователя."""
    user_id = message.from_id
    subscriptions = storage.get_user_subscriptions(user_id)

    if not subscriptions:
        await message.answer(
            Msg.NO_SUBSCRIPTIONS,
            keyboard=main_menu_inline(),
        )
        return

    # Формируем сообщение со списком подписок
    text = f"📬 Ваши подписки ({len(subscriptions)}):\n\n"

    for idx, sub in enumerate(subscriptions, 1):
        status = Format.SUBSCRIPTION_ACTIVE if sub.get("enabled", True) else Format.SUBSCRIPTION_PAUSED
        filter_text = format_filters(sub.get("filters", {}))

        text += f"{idx}. {status}\n"
        text += f"ID: {sub['id']}\n"
        text += f"{filter_text}\n\n"

    # Создаём клавиатуру с кнопками для каждой подписки
    kb = Keyboard(inline=True)

    for idx, sub in enumerate(subscriptions, 1):
        is_enabled = sub.get("enabled", True)
        prefix = Format.SUBSCRIPTION_BUTTON_ACTIVE_PREFIX if is_enabled else Format.SUBSCRIPTION_BUTTON_PAUSED_PREFIX
        kb.add(Text(f"{prefix}{idx}"))
        if idx % 2 == 0:
            kb.row()

    if len(subscriptions) % 2 != 0:
        kb.row()

    kb.add(Text(Button.MENU), color=KeyboardButtonColor.NEGATIVE)

    await message.answer(text, keyboard=kb.get_json())


@bot.on.message(text=Button.BACK_TO_SUBSCRIPTIONS)
async def back_to_subscriptions_handler(message: Message):
    """Обработчик кнопки возврата к подпискам."""
    await show_subscriptions(message)


@bot.on.message(text=[Button.TOGGLE_DISABLE, Button.TOGGLE_ENABLE])
async def toggle_subscription_handler(message: Message):
    """Обработчик переключения подписки."""
    user_id = message.from_id
    uid = str(user_id)

    from bot.bot_instance import search_sessions
    session = search_sessions.get(uid, {})
    sub_id = session.get("current_subscription_id")

    if not sub_id:
        await message.answer(
            Msg.ERROR_SUBSCRIPTION_NOT_FOUND,
            keyboard=main_menu_inline(),
        )
        return

    new_status = storage.toggle_subscription(user_id, sub_id)
    status_msg = Msg.SUBSCRIPTION_ENABLED if new_status else Msg.SUBSCRIPTION_DISABLED

    await message.answer(
        status_msg,
        keyboard=main_menu_inline(),
    )


@bot.on.message(text=Button.DELETE)
async def delete_subscription_handler(message: Message):
    """Обработчик удаления подписки (первый шаг - запрос подтверждения)."""
    user_id = message.from_id
    uid = str(user_id)

    from bot.bot_instance import search_sessions
    session = search_sessions.get(uid, {})
    sub_id = session.get("current_subscription_id")

    if not sub_id:
        await message.answer(
            Msg.ERROR_SUBSCRIPTION_NOT_FOUND,
            keyboard=main_menu_inline(),
        )
        return

    # Показываем подтверждение
    kb = Keyboard(inline=True)
    kb.add(Text(Button.CONFIRM_DELETE), color=KeyboardButtonColor.NEGATIVE)
    kb.add(Text(Button.CANCEL), color=KeyboardButtonColor.SECONDARY)

    await message.answer(
        Msg.SUBSCRIPTION_DELETE_CONFIRM,
        keyboard=kb.get_json(),
    )


@bot.on.message(text=Button.CONFIRM_DELETE)
async def confirm_delete_subscription_handler(message: Message):
    """Обработчик подтверждения удаления подписки."""
    user_id = message.from_id
    uid = str(user_id)

    from bot.bot_instance import search_sessions
    session = search_sessions.get(uid, {})
    sub_id = session.get("current_subscription_id")

    if not sub_id:
        await message.answer(
            Msg.ERROR_SUBSCRIPTION_NOT_FOUND,
            keyboard=main_menu_inline(),
        )
        return

    success = storage.delete_subscription(user_id, sub_id)

    if success:
        await message.answer(
            Msg.SUBSCRIPTION_DELETED,
            keyboard=main_menu_inline(),
        )
        logger.info("User %s deleted subscription %s", user_id, sub_id)
        # Очищаем сессию
        if "current_subscription_id" in session:
            del session["current_subscription_id"]
    else:
        await message.answer(
            Msg.ERROR_DELETE_FAILED,
            keyboard=main_menu_inline(),
        )


@bot.on.message(text=Button.CANCEL)
async def cancel_delete_subscription_handler(message: Message):
    """Обработчик отмены удаления подписки."""
    await message.answer(
        Msg.SUBSCRIPTION_DELETE_CANCELLED,
        keyboard=main_menu_inline(),
    )


def is_subscription_button(message: Message) -> bool:
    """Проверяет, является ли сообщение кнопкой выбора подписки."""
    text = (message.text or "").strip()
    return text.startswith(Format.SUBSCRIPTION_BUTTON_ACTIVE_PREFIX) or text.startswith(Format.SUBSCRIPTION_BUTTON_PAUSED_PREFIX)


@bot.on.message(func=is_subscription_button)
async def select_subscription_handler(message: Message):
    """Обработчик выбора конкретной подписки из списка."""
    text = (message.text or "").strip()
    user_id = message.from_id
    uid = str(user_id)
    subscriptions = storage.get_user_subscriptions(user_id)

    if not subscriptions:
        await message.answer(
            Msg.ERROR_SUBSCRIPTION_NOT_FOUND,
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
            Msg.ERROR_INVALID_SUBSCRIPTION_NUMBER,
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
    status = Format.SUBSCRIPTION_ACTIVE if is_enabled else Format.SUBSCRIPTION_PAUSED
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
        kb.add(Text(Button.TOGGLE_DISABLE))
    else:
        kb.add(Text(Button.TOGGLE_ENABLE), color=KeyboardButtonColor.POSITIVE)

    kb.add(Text(Button.DELETE), color=KeyboardButtonColor.NEGATIVE)
    kb.row()
    kb.add(Text(Button.BACK_TO_SUBSCRIPTIONS), color=KeyboardButtonColor.PRIMARY)

    await message.answer(response_text, keyboard=kb.get_json())


