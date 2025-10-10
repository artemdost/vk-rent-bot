"""
Обработчики для создания объявлений об аренде.
Включает FSM для сбора данных и публикации объявления.
"""
import logging
from typing import Optional
from vkbottle.bot import Message

from bot.bot_instance import bot, user_data
from bot.states import RentStates, STATE_PROMPTS
from bot.keyboards import (
    main_menu_inline,
    kb_for_state_inline,
    kb_preview_inline,
    kb_photos_inline,
)
from bot.services import (
    extract_photo_urls_from_message,
    upload_photos_to_group,
    send_to_scheduled,
)
from bot.utils import (
    extract_int,
    validate_phone,
    validate_district,
    format_preview_text,
    build_post_text,
)
from bot.config import DEFAULT_SCHEDULE_DELAY

logger = logging.getLogger("rent_handlers")


def state_keyboard(uid: str, state) -> str:
    """Возвращает клавиатуру для состояния с учётом режима редактирования."""
    editing = bool(user_data.get(uid, {}).get("back_to_preview"))
    return kb_for_state_inline(state, editing=editing)


def photos_keyboard(uid: str) -> str:
    """Возвращает клавиатуру для фото с учётом режима редактирования."""
    editing = bool(user_data.get(uid, {}).get("back_to_preview"))
    return kb_photos_inline(editing=editing)


async def prompt_for_state(message: Message, state):
    """Отправляет промпт для состояния аренды."""
    uid = str(message.from_id)
    user_data.setdefault(uid, {})
    prompt = STATE_PROMPTS.get(state, "Действие:")

    # Показываем текущее значение, если есть
    mapping = {
        RentStates.ADDRESS: "address",
        RentStates.FLOOR: "floor",
        RentStates.ROOMS: "rooms",
        RentStates.PRICE: "price",
        RentStates.DESCRIPTION: "description",
        RentStates.FIO: "fio",
        RentStates.PHONE: "phone",
    }

    field_val = user_data[uid].get(mapping[state]) if state in mapping else None
    extra = f"\n(текущее: {field_val})" if field_val else ""
    editing = bool(user_data[uid].get("back_to_preview"))

    await message.answer(
        prompt + extra, keyboard=kb_for_state_inline(state, editing=editing)
    )


async def maybe_back_to_preview(message: Message, uid: str) -> bool:
    """
    Если установлен флаг back_to_preview — показываем обновлённый превью.
    Возвращает True, если вернулись к превью.
    """
    if user_data.get(uid, {}).pop("back_to_preview", False):
        draft = user_data.get(uid, {})
        preview_text = format_preview_text(draft)

        await bot.state_dispenser.set(message.peer_id, RentStates.PREVIEW)
        await message.answer(preview_text, keyboard=kb_preview_inline(draft))
        return True
    return False


# ===== HANDLERS =====


@bot.on.message(text="Выложить")
async def post_rent_start(message: Message):
    """Начало создания объявления."""
    uid = str(message.from_id)
    user_data[uid] = {}
    await bot.state_dispenser.set(message.peer_id, RentStates.DISTRICT)
    await message.answer(
        STATE_PROMPTS[RentStates.DISTRICT],
        keyboard=state_keyboard(uid, RentStates.DISTRICT),
    )


@bot.on.message(state=RentStates.DISTRICT)
async def district_handler(message: Message):
    """Обработчик выбора района."""
    uid = str(message.from_id)
    peer = message.peer_id
    text = (message.text or "").strip()
    user_data.setdefault(uid, {})

    if text == "Меню":
        try:
            await bot.state_dispenser.delete(peer)
        except (KeyError, Exception):
            pass
        await message.answer("Вы вернулись в меню.", keyboard=main_menu_inline())
        return

    if text == "Отмена":
        if await maybe_back_to_preview(message, uid):
            return

    if not validate_district(text):
        await message.answer(
            "Пожалуйста, выберите район из кнопок.",
            keyboard=state_keyboard(uid, RentStates.DISTRICT),
        )
        return

    user_data[uid]["district"] = text
    await bot.state_dispenser.set(peer, RentStates.ADDRESS)
    await prompt_for_state(message, RentStates.ADDRESS)


@bot.on.message(state=RentStates.ADDRESS)
async def address_handler(message: Message):
    """Обработчик ввода адреса."""
    uid = str(message.from_id)
    peer = message.peer_id
    text = (message.text or "").strip()
    user_data.setdefault(uid, {})

    if text == "Меню":
        try:
            await bot.state_dispenser.delete(peer)
        except (KeyError, Exception):
            pass
        await message.answer("Вы вернулись в меню.", keyboard=main_menu_inline())
        return

    if text == "Отмена":
        if await maybe_back_to_preview(message, uid):
            return
        text = "Назад"

    if text == "Назад":
        await bot.state_dispenser.set(peer, RentStates.DISTRICT)
        await message.answer(
            STATE_PROMPTS[RentStates.DISTRICT],
            keyboard=state_keyboard(uid, RentStates.DISTRICT),
        )
        return

    user_data[uid]["address"] = message.text

    if await maybe_back_to_preview(message, uid):
        return

    await bot.state_dispenser.set(peer, RentStates.FLOOR)
    await prompt_for_state(message, RentStates.FLOOR)


@bot.on.message(state=RentStates.FLOOR)
async def floor_handler(message: Message):
    """Обработчик ввода этажа."""
    uid = str(message.from_id)
    peer = message.peer_id
    text = (message.text or "").strip()
    user_data.setdefault(uid, {})

    if text == "Меню":
        try:
            await bot.state_dispenser.delete(peer)
        except (KeyError, Exception):
            pass
        await message.answer("Вы вернулись в меню.", keyboard=main_menu_inline())
        return

    if text == "Отмена":
        if await maybe_back_to_preview(message, uid):
            return
        text = "Назад"

    if text == "Назад":
        await bot.state_dispenser.set(peer, RentStates.ADDRESS)
        await prompt_for_state(message, RentStates.ADDRESS)
        return

    try:
        value = int(text)
        if value <= 0:
            raise ValueError
        user_data[uid]["floor"] = value
    except Exception:
        await message.answer(
            "Этаж должен быть положительным числом. Введите цифрами.",
            keyboard=state_keyboard(uid, RentStates.FLOOR),
        )
        return

    if await maybe_back_to_preview(message, uid):
        return

    await bot.state_dispenser.set(peer, RentStates.ROOMS)
    await prompt_for_state(message, RentStates.ROOMS)


@bot.on.message(state=RentStates.ROOMS)
async def rooms_handler(message: Message):
    """Обработчик ввода количества комнат."""
    uid = str(message.from_id)
    peer = message.peer_id
    text = (message.text or "").strip()
    user_data.setdefault(uid, {})

    if text == "Меню":
        try:
            await bot.state_dispenser.delete(peer)
        except (KeyError, Exception):
            pass
        await message.answer("Вы вернулись в меню.", keyboard=main_menu_inline())
        return

    if text == "Отмена":
        if await maybe_back_to_preview(message, uid):
            return
        text = "Назад"

    if text == "Назад":
        await bot.state_dispenser.set(peer, RentStates.FLOOR)
        await prompt_for_state(message, RentStates.FLOOR)
        return

    try:
        value = int(text)
        if value <= 0:
            raise ValueError
        user_data[uid]["rooms"] = value
    except Exception:
        await message.answer(
            "Количество комнат должно быть положительным числом. Введите цифрами.",
            keyboard=state_keyboard(uid, RentStates.ROOMS),
        )
        return

    if await maybe_back_to_preview(message, uid):
        return

    await bot.state_dispenser.set(peer, RentStates.PRICE)
    await prompt_for_state(message, RentStates.PRICE)


@bot.on.message(state=RentStates.PRICE)
async def price_handler(message: Message):
    """Обработчик ввода цены."""
    uid = str(message.from_id)
    peer = message.peer_id
    text = (message.text or "").strip()
    user_data.setdefault(uid, {})

    if text == "Меню":
        try:
            await bot.state_dispenser.delete(peer)
        except (KeyError, Exception):
            pass
        await message.answer("Вы вернулись в меню.", keyboard=main_menu_inline())
        return

    if text == "Отмена":
        if await maybe_back_to_preview(message, uid):
            return
        text = "Назад"

    if text == "Назад":
        await bot.state_dispenser.set(peer, RentStates.ROOMS)
        await prompt_for_state(message, RentStates.ROOMS)
        return

    try:
        value = extract_int(text)
    except Exception:
        value = None

    if value is None:
        await message.answer(
            "Цена должна быть числом. Попробуйте ещё раз.",
            keyboard=state_keyboard(uid, RentStates.PRICE),
        )
        return

    if value <= 0:
        await message.answer(
            "Цена должна быть положительной. Попробуйте ещё раз.",
            keyboard=state_keyboard(uid, RentStates.PRICE),
        )
        return

    user_data[uid]["price"] = int(value)

    if await maybe_back_to_preview(message, uid):
        return

    await bot.state_dispenser.set(peer, RentStates.DESCRIPTION)
    await prompt_for_state(message, RentStates.DESCRIPTION)


@bot.on.message(state=RentStates.DESCRIPTION)
async def description_handler(message: Message):
    """Обработчик ввода описания."""
    uid = str(message.from_id)
    peer = message.peer_id
    text = (message.text or "").strip()
    user_data.setdefault(uid, {})

    if text == "Меню":
        try:
            await bot.state_dispenser.delete(peer)
        except (KeyError, Exception):
            pass
        await message.answer("Вы вернулись в меню.", keyboard=main_menu_inline())
        return

    if text == "Отмена":
        if await maybe_back_to_preview(message, uid):
            return
        text = "Назад"

    if text == "Назад":
        await bot.state_dispenser.set(peer, RentStates.PRICE)
        await prompt_for_state(message, RentStates.PRICE)
        return

    user_data[uid]["description"] = message.text

    await bot.state_dispenser.set(peer, RentStates.PHOTOS)
    await message.answer(
        STATE_PROMPTS.get(RentStates.PHOTOS, "Прикрепите фото или Пропустить."),
        keyboard=photos_keyboard(uid),
    )


@bot.on.message(state=RentStates.PHOTOS)
async def photos_handler(message: Message):
    """Обработчик загрузки фото."""
    uid = str(message.from_id)
    peer = message.peer_id
    text = (message.text or "").strip()
    user_data.setdefault(uid, {})

    if text == "Меню":
        try:
            await bot.state_dispenser.delete(peer)
        except (KeyError, Exception):
            pass
        await message.answer("Вы вернулись в меню.", keyboard=main_menu_inline())
        return

    if text == "Отмена":
        if await maybe_back_to_preview(message, uid):
            return
        text = "Назад"

    if text == "Назад":
        await bot.state_dispenser.set(peer, RentStates.DESCRIPTION)
        await prompt_for_state(message, RentStates.DESCRIPTION)
        return

    if text in ("Пропустить", "Готово"):
        await bot.state_dispenser.set(peer, RentStates.FIO)
        await prompt_for_state(message, RentStates.FIO)
        return

    # Извлекаем фото из сообщения
    photo_urls = await extract_photo_urls_from_message(message)

    if photo_urls:
        stored = user_data[uid].setdefault("photo_urls", [])
        new_urls = [url for url in photo_urls if url not in stored]

        if not new_urls:
            await message.answer(
                "Эти фото уже прикреплены. Добавьте новые или используйте кнопки.",
                keyboard=photos_keyboard(uid),
            )
            return

        stored.extend(new_urls)
        added = len(new_urls)
        total = len(stored)

        await message.answer(
            f"Добавлено {added} фото. Всего: {total}.",
            keyboard=photos_keyboard(uid),
        )
        return

    await message.answer(
        "Пожалуйста, пришлите фото (файл) или нажмите «Пропустить»/«Готово».",
        keyboard=photos_keyboard(uid),
    )


@bot.on.message(state=RentStates.FIO)
async def fio_handler(message: Message):
    """Обработчик ввода ФИО."""
    uid = str(message.from_id)
    peer = message.peer_id
    text = (message.text or "").strip()
    user_data.setdefault(uid, {})

    if text == "Меню":
        try:
            await bot.state_dispenser.delete(peer)
        except (KeyError, Exception):
            pass
        await message.answer("Вы вернулись в меню.", keyboard=main_menu_inline())
        return

    if text == "Отмена":
        if await maybe_back_to_preview(message, uid):
            return
        text = "Назад"

    if text == "Назад":
        await bot.state_dispenser.set(peer, RentStates.PHOTOS)
        await message.answer(
            STATE_PROMPTS.get(RentStates.PHOTOS, "Прикрепите фото или Пропустить."),
            keyboard=photos_keyboard(uid),
        )
        return

    if not text or len(text) < 2:
        await message.answer(
            "Пожалуйста, укажите ФИО (имя и фамилия).",
            keyboard=state_keyboard(uid, RentStates.FIO),
        )
        return

    user_data[uid]["fio"] = text
    await bot.state_dispenser.set(peer, RentStates.PHONE)
    await prompt_for_state(message, RentStates.PHONE)


@bot.on.message(state=RentStates.PHONE)
async def phone_handler(message: Message):
    """Обработчик ввода телефона."""
    uid = str(message.from_id)
    peer = message.peer_id
    text = (message.text or "").strip()
    user_data.setdefault(uid, {})

    if text == "Меню":
        try:
            await bot.state_dispenser.delete(peer)
        except (KeyError, Exception):
            pass
        await message.answer("Вы вернулись в меню.", keyboard=main_menu_inline())
        return

    if text == "Отмена":
        if await maybe_back_to_preview(message, uid):
            return
        text = "Назад"

    if text == "Назад":
        await bot.state_dispenser.set(peer, RentStates.FIO)
        await prompt_for_state(message, RentStates.FIO)
        return

    is_valid, normalized = validate_phone(text)

    if not is_valid:
        await message.answer(
            "Неверный номер — должно быть не менее 7 цифр. Попробуйте ещё раз.",
            keyboard=state_keyboard(uid, RentStates.PHONE),
        )
        return

    user_data[uid]["phone"] = normalized

    # Показываем превью
    draft = user_data[uid]
    preview_text = format_preview_text(draft)

    await bot.state_dispenser.set(peer, RentStates.PREVIEW)
    await message.answer(preview_text, keyboard=kb_preview_inline(draft))


@bot.on.message(text="Отправить")
async def send_scheduled_handler(message: Message):
    """Отправка объявления в отложенные записи."""
    uid = str(message.from_id)
    peer = message.peer_id
    draft = user_data.get(uid)

    if not draft:
        await message.answer(
            "Нет черновика для отправки.", keyboard=main_menu_inline()
        )
        return

    text = build_post_text(draft)
    if not isinstance(text, str):
        text = str(text)

    attachments: Optional[str] = None
    photo_urls = draft.get("photo_urls") or []

    if photo_urls:
        await message.answer(
            "Начинаю загрузку фото в сообщество... (это может занять некоторое время)"
        )
        upload_resp = upload_photos_to_group(photo_urls)

        if "error" in upload_resp:
            err = upload_resp.get("error", {})
            await message.answer(
                f"Ошибка при загрузке фото: {err.get('error_msg')}",
                keyboard=main_menu_inline(),
            )
            return

        attachments = upload_resp.get("response", {}).get("attachments")

    try:
        resp = send_to_scheduled(
            text=text, attachments=attachments, delay_seconds=DEFAULT_SCHEDULE_DELAY
        )
    except Exception as e:
        await message.answer(
            f"Ошибка при отправке: {e}", keyboard=main_menu_inline()
        )
        return

    if "error" in resp:
        err = resp.get("error", {})
        await message.answer(
            f"Ошибка при отправке в отложенные: {err.get('error_msg')}",
            keyboard=main_menu_inline(),
        )
        return

    post_id = resp.get("response", {}).get("post_id")
    if post_id:
        await message.answer(
            f"✅ Готово — объявление отправлено в отложенные.",
            keyboard=main_menu_inline(),
        )
    else:
        await message.answer(
            "Готово — объявление отправлено в отложенные. Проверьте админку сообщества.",
            keyboard=main_menu_inline(),
        )

    # Очищаем черновик и состояние
    user_data.pop(uid, None)
    try:
        try:
            await bot.state_dispenser.delete(peer)
        except (KeyError, Exception):
            pass
    except:
        pass


# Обработчики редактирования полей из превью
@bot.on.message(text="Район")
async def edit_district(message: Message):
    uid = str(message.from_id)
    user_data.setdefault(uid, {})["back_to_preview"] = True
    await bot.state_dispenser.set(message.peer_id, RentStates.DISTRICT)
    await message.answer(
        STATE_PROMPTS[RentStates.DISTRICT],
        keyboard=state_keyboard(uid, RentStates.DISTRICT),
    )


@bot.on.message(text="Адрес")
async def edit_address(message: Message):
    uid = str(message.from_id)
    user_data.setdefault(uid, {})["back_to_preview"] = True
    await bot.state_dispenser.set(message.peer_id, RentStates.ADDRESS)
    await prompt_for_state(message, RentStates.ADDRESS)


@bot.on.message(text="Этаж")
async def edit_floor(message: Message):
    uid = str(message.from_id)
    user_data.setdefault(uid, {})["back_to_preview"] = True
    await bot.state_dispenser.set(message.peer_id, RentStates.FLOOR)
    await prompt_for_state(message, RentStates.FLOOR)


@bot.on.message(text="Комнаты")
async def edit_rooms(message: Message):
    uid = str(message.from_id)
    user_data.setdefault(uid, {})["back_to_preview"] = True
    await bot.state_dispenser.set(message.peer_id, RentStates.ROOMS)
    await prompt_for_state(message, RentStates.ROOMS)


@bot.on.message(text="Цена")
async def edit_price(message: Message):
    uid = str(message.from_id)
    user_data.setdefault(uid, {})["back_to_preview"] = True
    await bot.state_dispenser.set(message.peer_id, RentStates.PRICE)
    await prompt_for_state(message, RentStates.PRICE)


@bot.on.message(text="Описание")
async def edit_description(message: Message):
    uid = str(message.from_id)
    user_data.setdefault(uid, {})["back_to_preview"] = True
    await bot.state_dispenser.set(message.peer_id, RentStates.DESCRIPTION)
    await prompt_for_state(message, RentStates.DESCRIPTION)


@bot.on.message(text="ФИО")
async def edit_fio(message: Message):
    uid = str(message.from_id)
    user_data.setdefault(uid, {})["back_to_preview"] = True
    await bot.state_dispenser.set(message.peer_id, RentStates.FIO)
    await prompt_for_state(message, RentStates.FIO)


@bot.on.message(text="Телефон")
async def edit_phone(message: Message):
    uid = str(message.from_id)
    user_data.setdefault(uid, {})["back_to_preview"] = True
    await bot.state_dispenser.set(message.peer_id, RentStates.PHONE)
    await prompt_for_state(message, RentStates.PHONE)
