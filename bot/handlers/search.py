"""
Обработчики для поиска объявлений.
Включает FSM для поиска и отображение результатов.
"""
import logging
from typing import Dict, Any
from vkbottle.bot import Message

from bot.bot_instance import bot, search_sessions
from bot.config import (
    GROUP_ID,
    MAX_SEARCHES_UNSUBSCRIBED,
    SEARCH_RESULTS_PAGE_SIZE,
)
from bot.states import SearchStates, SEARCH_PROMPTS
from bot.keyboards import (
    main_menu_inline,
    subscription_keyboard,
    search_kb_for_state_inline,
    search_results_keyboard,
)
from bot.services import check_subscription, search_posts
from bot.utils import extract_int, format_search_result, validate_search_district
from storage import storage

logger = logging.getLogger("search_handlers")


def get_search_session(uid: str) -> Dict[str, Any]:
    """Получает или создаёт сессию поиска для пользователя."""
    return search_sessions.setdefault(uid, {})


def _search_reset(uid: str) -> None:
    """Сбрасывает сессию поиска пользователя."""
    search_sessions.pop(uid, None)


async def prompt_search_state(message: Message, state) -> None:
    """Отправляет промпт для состояния поиска."""
    prompt = SEARCH_PROMPTS.get(state, "Введите значение:")
    await message.answer(prompt, keyboard=search_kb_for_state_inline(state))


async def send_search_results_chunk(
    message: Message, uid: str, chunk_size: int = SEARCH_RESULTS_PAGE_SIZE
) -> bool:
    """
    Отправляет чанк результатов поиска.
    Возвращает True, если есть ещё результаты.
    """
    session = get_search_session(uid)
    results = session.get("results") or []
    offset = session.get("results_offset", 0)
    total = len(results)

    if offset >= total:
        return False

    next_offset = min(total, offset + chunk_size)

    for index in range(offset, next_offset):
        match = results[index]
        item = match["item"]
        text = format_search_result(index + 1, item)
        post_id = item.get("id")

        if post_id is not None:
            owner_part = -abs(int(GROUP_ID))
            attachment = f"wall{owner_part}_{post_id}"
            await message.answer(text, attachment=attachment)
        else:
            await message.answer(text)

    session["results_offset"] = next_offset

    if next_offset < total:
        await message.answer(
            f"Показал {next_offset} из {total}. Продолжить?",
            keyboard=search_results_keyboard(True),
        )
        return True

    await message.answer(
        "Это все подходящие объявления.",
        keyboard=main_menu_inline(),
    )
    return False


async def run_search_and_reply(message: Message, uid: str) -> None:
    """Выполняет поиск и отправляет результаты."""
    session = get_search_session(uid)
    filters = {
        "district": session.get("district"),
        "price_min": session.get("price_min"),
        "price_max": session.get("price_max"),
        "rooms": session.get("rooms"),
        "recent_days": session.get("recent_days"),
    }

    matches, error = search_posts(filters)

    if error:
        await message.answer(
            f"Не удалось получить объявления: {error}",
            keyboard=main_menu_inline(),
        )
        try:
            try:
                await bot.state_dispenser.delete(message.peer_id)
            except (KeyError, Exception):
                pass
        except (KeyError, Exception):
            pass
        _search_reset(uid)
        return

    if not matches:
        await message.answer(
            "По заданным фильтрам ничего не найдено. Попробуйте изменить параметры.",
            keyboard=main_menu_inline(),
        )
        try:
            try:
                await bot.state_dispenser.delete(message.peer_id)
            except (KeyError, Exception):
                pass
        except (KeyError, Exception):
            pass
        _search_reset(uid)
        return

    session["results"] = matches
    session["results_offset"] = 0

    total_found = len(matches)
    await message.answer(f"Нашёл {total_found} подходящих объявлений.")

    has_more = await send_search_results_chunk(
        message, uid, chunk_size=SEARCH_RESULTS_PAGE_SIZE
    )

    if has_more:
        await bot.state_dispenser.set(message.peer_id, SearchStates.RESULTS)
    else:
        try:
            try:
                await bot.state_dispenser.delete(message.peer_id)
            except (KeyError, Exception):
                pass
        except (KeyError, Exception):
            pass
        _search_reset(uid)


# ===== HANDLERS =====


@bot.on.message(text="Посмотреть")
async def view_rents(message: Message):
    """Начало поиска объявлений."""
    uid = str(message.from_id)
    user_id = message.from_id

    # Проверяем подписку
    is_subscribed = await check_subscription(user_id)

    if not is_subscribed:
        # Проверяем лимит поисков
        search_count = storage.get_search_count(user_id)

        if search_count >= MAX_SEARCHES_UNSUBSCRIBED:
            await message.answer(
                f"❌ Вы использовали все {MAX_SEARCHES_UNSUBSCRIBED} бесплатных поиска.\n\n"
                f"Чтобы продолжить пользоваться поиском без ограничений, "
                f"подпишитесь на наше сообщество:\n"
                f"https://vk.com/club{GROUP_ID}\n\n"
                f"После подписки нажмите «Проверить подписку».",
                keyboard=subscription_keyboard(),
            )
            return

        # Увеличиваем счетчик
        new_count = storage.increment_search_count(user_id)
        remaining = MAX_SEARCHES_UNSUBSCRIBED - new_count

        if remaining > 0:
            await message.answer(
                f"ℹ️ У вас осталось {remaining} бесплатных поисков.\n"
                f"Подпишитесь на сообщество для неограниченного доступа:\n"
                f"https://vk.com/club{GROUP_ID}"
            )

    # Начинаем поиск
    search_sessions[uid] = {}
    await bot.state_dispenser.set(message.peer_id, SearchStates.DISTRICT)
    await message.answer("Подберём объявления из сообщества по вашим фильтрам.")
    await prompt_search_state(message, SearchStates.DISTRICT)


@bot.on.message(text="Проверить подписку")
async def check_subscription_handler(message: Message):
    """Проверка подписки на сообщество."""
    user_id = message.from_id

    is_subscribed = await check_subscription(user_id)

    if is_subscribed:
        # Сбрасываем счетчик поисков
        storage.reset_search_count(user_id)

        await message.answer(
            "✅ Отлично! Вы подписаны на сообщество.\n"
            "Теперь вы можете использовать поиск без ограничений!",
            keyboard=main_menu_inline(),
        )
    else:
        search_count = storage.get_search_count(user_id)
        remaining = MAX_SEARCHES_UNSUBSCRIBED - search_count

        await message.answer(
            f"❌ Вы еще не подписаны на сообщество.\n\n"
            f"Подпишитесь здесь: https://vk.com/club{GROUP_ID}\n\n"
            f"Осталось бесплатных поисков: {remaining}",
            keyboard=subscription_keyboard(),
        )


@bot.on.message(state=SearchStates.DISTRICT)
async def search_district_handler(message: Message):
    """Обработчик выбора района для поиска."""
    uid = str(message.from_id)
    peer = message.peer_id
    text = (message.text or "").strip()

    if text == "Меню":
        _search_reset(uid)
        try:
            await bot.state_dispenser.delete(peer)
        except (KeyError, Exception):
            pass
        await message.answer("Вы вернулись в меню.", keyboard=main_menu_inline())
        return

    if not validate_search_district(text):
        await message.answer(
            "Пожалуйста, выберите район из кнопок или нажмите «Любой».",
            keyboard=search_kb_for_state_inline(SearchStates.DISTRICT),
        )
        return

    session = get_search_session(uid)
    session["district"] = None if text == "Любой" else text

    await bot.state_dispenser.set(peer, SearchStates.PRICE_MIN)
    await prompt_search_state(message, SearchStates.PRICE_MIN)


@bot.on.message(state=SearchStates.PRICE_MIN)
async def search_price_min_handler(message: Message):
    """Обработчик минимальной цены."""
    uid = str(message.from_id)
    peer = message.peer_id
    text = (message.text or "").strip()

    if text == "Меню":
        _search_reset(uid)
        try:
            await bot.state_dispenser.delete(peer)
        except (KeyError, Exception):
            pass
        await message.answer("Вы вернулись в меню.", keyboard=main_menu_inline())
        return

    if text == "Назад":
        await bot.state_dispenser.set(peer, SearchStates.DISTRICT)
        await prompt_search_state(message, SearchStates.DISTRICT)
        return

    session = get_search_session(uid)
    session.pop("price_max", None)  # Сбрасываем max при изменении min

    if text.lower() in {"", "пропустить"}:
        session["price_min"] = None
    else:
        value = extract_int(text)
        if value is None:
            await message.answer(
                "Минимальная цена должна быть числом. Попробуйте ещё раз или нажмите «Пропустить».",
                keyboard=search_kb_for_state_inline(SearchStates.PRICE_MIN),
            )
            return
        session["price_min"] = value

    await bot.state_dispenser.set(peer, SearchStates.PRICE_MAX)
    await prompt_search_state(message, SearchStates.PRICE_MAX)


@bot.on.message(state=SearchStates.PRICE_MAX)
async def search_price_max_handler(message: Message):
    """Обработчик максимальной цены."""
    uid = str(message.from_id)
    peer = message.peer_id
    text = (message.text or "").strip()

    if text == "Меню":
        _search_reset(uid)
        try:
            await bot.state_dispenser.delete(peer)
        except (KeyError, Exception):
            pass
        await message.answer("Вы вернулись в меню.", keyboard=main_menu_inline())
        return

    if text == "Назад":
        await bot.state_dispenser.set(peer, SearchStates.PRICE_MIN)
        await prompt_search_state(message, SearchStates.PRICE_MIN)
        return

    session = get_search_session(uid)

    if text.lower() in {"", "пропустить"}:
        session["price_max"] = None
    else:
        value = extract_int(text)
        if value is None:
            await message.answer(
                "Максимальная цена должна быть числом. Попробуйте ещё раз или нажмите «Пропустить».",
                keyboard=search_kb_for_state_inline(SearchStates.PRICE_MAX),
            )
            return

        price_min = session.get("price_min")
        if price_min is not None and value < price_min:
            await message.answer(
                "Максимальная цена не может быть меньше минимальной. Укажите другое значение или нажмите «Пропустить».",
                keyboard=search_kb_for_state_inline(SearchStates.PRICE_MAX),
            )
            return
        session["price_max"] = value

    await bot.state_dispenser.set(peer, SearchStates.ROOMS)
    await prompt_search_state(message, SearchStates.ROOMS)


@bot.on.message(state=SearchStates.ROOMS)
async def search_rooms_handler(message: Message):
    """Обработчик количества комнат."""
    uid = str(message.from_id)
    peer = message.peer_id
    text = (message.text or "").strip()

    if text == "Меню":
        _search_reset(uid)
        try:
            await bot.state_dispenser.delete(peer)
        except (KeyError, Exception):
            pass
        await message.answer("Вы вернулись в меню.", keyboard=main_menu_inline())
        return

    if text == "Назад":
        await bot.state_dispenser.set(peer, SearchStates.PRICE_MAX)
        await prompt_search_state(message, SearchStates.PRICE_MAX)
        return

    session = get_search_session(uid)

    if text.lower() in {"", "пропустить"}:
        session["rooms"] = None
    else:
        value = extract_int(text)
        if value is None:
            await message.answer(
                "Количество комнат должно быть числом. Попробуйте ещё раз или нажмите «Пропустить».",
                keyboard=search_kb_for_state_inline(SearchStates.ROOMS),
            )
            return
        session["rooms"] = value

    await bot.state_dispenser.set(peer, SearchStates.RECENT_DAYS)
    await prompt_search_state(message, SearchStates.RECENT_DAYS)


@bot.on.message(state=SearchStates.RECENT_DAYS)
async def search_recent_days_handler(message: Message):
    """Обработчик фильтра по давности."""
    uid = str(message.from_id)
    peer = message.peer_id
    text = (message.text or "").strip()

    if text == "Выход":
        _search_reset(uid)
        try:
            await bot.state_dispenser.delete(peer)
        except (KeyError, Exception):
            pass
        await message.answer("Вы вернулись в меню.", keyboard=main_menu_inline())
        return

    if text == "Назад":
        await bot.state_dispenser.set(peer, SearchStates.ROOMS)
        await prompt_search_state(message, SearchStates.ROOMS)
        return

    normalized = text.lower()
    session = get_search_session(uid)

    if normalized in {"", "не важно", "неважно"}:
        session["recent_days"] = None
    elif "7" in normalized:
        session["recent_days"] = 7
    elif "30" in normalized:
        session["recent_days"] = 30
    else:
        await message.answer(
            "Пожалуйста, выберите вариант из меню.",
            keyboard=search_kb_for_state_inline(SearchStates.RECENT_DAYS),
        )
        return

    try:
        await bot.state_dispenser.delete(peer)
    except (KeyError, Exception):
        pass

    await run_search_and_reply(message, uid)


@bot.on.message(state=SearchStates.RESULTS)
async def search_results_handler(message: Message):
    """Обработчик навигации по результатам поиска."""
    uid = str(message.from_id)
    peer = message.peer_id
    text = (message.text or "").strip().lower()

    session = search_sessions.get(uid)
    if not session or not session.get("results"):
        try:
            await bot.state_dispenser.delete(peer)
        except (KeyError, Exception):
            pass
        await message.answer(
            "Результаты поиска недоступны. Попробуйте запустить поиск заново.",
            keyboard=main_menu_inline(),
        )
        _search_reset(uid)
        return

    if text in {"меню", "в меню", "выход"}:
        _search_reset(uid)
        try:
            await bot.state_dispenser.delete(peer)
        except (KeyError, Exception):
            pass
        await message.answer("Вы вернулись в меню.", keyboard=main_menu_inline())
        return

    if text in {"ещё 10", "ещё", "еще 10", "еще", "продолжить"}:
        has_more = await send_search_results_chunk(
            message, uid, chunk_size=SEARCH_RESULTS_PAGE_SIZE
        )
        if not has_more:
            try:
                await bot.state_dispenser.delete(peer)
            except (KeyError, Exception):
                pass
            _search_reset(uid)
        return

    has_more = session.get("results_offset", 0) < len(session.get("results", []))
    keyboard = search_results_keyboard(has_more) if has_more else main_menu_inline()
    await message.answer(
        "Пожалуйста, используйте кнопки для навигации по результатам.", keyboard=keyboard
    )
