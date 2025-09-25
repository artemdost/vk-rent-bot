# post_flow.py
import re
from typing import List, Dict, Any, Optional
from vkbottle.bot import Message
from core import (
    bot,
    user_data,
    RentStates,
    main_menu_inline,
    kb_for_state_inline,
    kb_preview_inline,
    kb_photos_inline,
    prompt_for_state,
    STATE_PROMPTS,
)
from post_submit import send_to_scheduled, build_text_from_draft, upload_photos_to_group

# ---------------------------
# Utility helpers
# ---------------------------
def extract_photo_urls_from_message(message: Message) -> List[str]:
    """
    Robustly extract photo URLs from message.attachments (works for vkbottle Attachment objects or dict-like).
    Chooses the largest size (last in sizes array).
    """
    urls: List[str] = []
    atts = getattr(message, "attachments", None) or []
    for a in atts:
        try:
            photo = getattr(a, "photo", None)
            if photo is None:
                raw = a if isinstance(a, dict) else getattr(a, "__dict__", {})
                photo = raw.get("photo")
            if not photo:
                continue
            sizes = getattr(photo, "sizes", None) or photo.get("sizes", [])
            if not sizes:
                # sometimes photo has direct 'photo_604' etc — try to pick any url-like field
                if isinstance(photo, dict):
                    for _, v in photo.items():
                        if isinstance(v, str) and v.startswith("http"):
                            urls.append(v)
                            break
                continue
            size = sizes[-1]
            url = getattr(size, "url", None) or size.get("url")
            if url:
                urls.append(url)
        except Exception:
            continue
    return urls

async def maybe_back_to_preview(message: Message, uid: str) -> bool:
    """
    Если установлен флаг back_to_preview — показываем обновлённый превью и возвращаем True.
    """
    if user_data.get(uid, {}).pop("back_to_preview", False):
        draft = user_data.get(uid, {})
        preview_text = (
            f"📌 Обновлённый предпросмотр:\n\n"
            f"🏙 Район: {draft.get('district','—')}\n"
            f"📍 Адрес: {draft.get('address','—')}\n"
            f"🏢 Этаж: {draft.get('floor','—')}\n"
            f"🚪 Комнат: {draft.get('rooms','—')}\n"
            f"💰 Цена: {draft.get('price','—')}\n"
            f"📝 Описание:\n{draft.get('description','—')}\n\n"
            f"👤 Контакт: {draft.get('fio','—')}\n"
            f"📞 Телефон: {draft.get('phone','—')}\n\n"
            "Нажмите «Отправить в отложенные» или продолжите редактирование."
        )
        await bot.state_dispenser.set(message.peer_id, RentStates.PREVIEW)
        await message.answer(preview_text, keyboard=kb_preview_inline(draft))
        return True
    return False

# ---------------------------
# Entry / Menu
# ---------------------------
@bot.on.message(text="/start")
async def start_command(message: Message):
    await message.answer("Привет! Выберите действие:", keyboard=main_menu_inline())

@bot.on.message(text="Посмотреть объявления")
async def view_rents(message: Message):
    await message.answer("Список объявлений пока не реализован.", keyboard=main_menu_inline())

@bot.on.message(text="Выложить объявление")
async def post_rent_start(message: Message):
    uid = str(message.from_id)
    user_data[uid] = {}
    await bot.state_dispenser.set(message.peer_id, RentStates.DISTRICT)
    await message.answer(STATE_PROMPTS[RentStates.DISTRICT], keyboard=kb_for_state_inline(RentStates.DISTRICT))

# ---------------------------
# DISTRICT
# ---------------------------
@bot.on.message(state=RentStates.DISTRICT)
async def district_handler(message: Message):
    uid = str(message.from_id)
    peer = message.peer_id
    text = (message.text or "").strip()
    user_data.setdefault(uid, {})

    if text == "Меню":
        await bot.state_dispenser.delete(peer)
        await message.answer("Вы вернулись в меню.", keyboard=main_menu_inline())
        return

    valid = {"Центр", "Север", "Юг", "Восток", "Запад"}
    if text not in valid:
        await message.answer("Пожалуйста, выберите район из кнопок.", keyboard=kb_for_state_inline(RentStates.DISTRICT))
        return

    user_data[uid]["district"] = text
    await bot.state_dispenser.set(peer, RentStates.ADDRESS)
    await prompt_for_state(message, RentStates.ADDRESS)

# ---------------------------
# ADDRESS
# ---------------------------
@bot.on.message(state=RentStates.ADDRESS)
async def address_handler(message: Message):
    uid = str(message.from_id)
    peer = message.peer_id
    text = (message.text or "").strip()
    user_data.setdefault(uid, {})

    if text == "Меню":
        await bot.state_dispenser.delete(peer)
        await message.answer("Вы вернулись в меню.", keyboard=main_menu_inline())
        return
    if text == "Назад":
        await bot.state_dispenser.set(peer, RentStates.DISTRICT)
        await message.answer(STATE_PROMPTS[RentStates.DISTRICT], keyboard=kb_for_state_inline(RentStates.DISTRICT))
        return

    user_data[uid]["address"] = message.text
    if await maybe_back_to_preview(message, uid):
        return

    await bot.state_dispenser.set(peer, RentStates.FLOOR)
    await prompt_for_state(message, RentStates.FLOOR)

# ---------------------------
# FLOOR
# ---------------------------
@bot.on.message(state=RentStates.FLOOR)
async def floor_handler(message: Message):
    uid = str(message.from_id)
    peer = message.peer_id
    text = (message.text or "").strip()
    user_data.setdefault(uid, {})

    if text == "Меню":
        await bot.state_dispenser.delete(peer)
        await message.answer("Вы вернулись в меню.", keyboard=main_menu_inline())
        return
    if text == "Назад":
        await bot.state_dispenser.set(peer, RentStates.ADDRESS)
        await prompt_for_state(message, RentStates.ADDRESS)
        return

    try:
        user_data[uid]["floor"] = int(text)
    except Exception:
        await message.answer("Этаж должен быть числом. Введите цифрами.", keyboard=kb_for_state_inline(RentStates.FLOOR))
        return

    if await maybe_back_to_preview(message, uid):
        return

    await bot.state_dispenser.set(peer, RentStates.ROOMS)
    await prompt_for_state(message, RentStates.ROOMS)

# ---------------------------
# ROOMS
# ---------------------------
@bot.on.message(state=RentStates.ROOMS)
async def rooms_handler(message: Message):
    uid = str(message.from_id)
    peer = message.peer_id
    text = (message.text or "").strip()
    user_data.setdefault(uid, {})

    if text == "Меню":
        await bot.state_dispenser.delete(peer)
        await message.answer("Вы вернулись в меню.", keyboard=main_menu_inline())
        return
    if text == "Назад":
        await bot.state_dispenser.set(peer, RentStates.FLOOR)
        await prompt_for_state(message, RentStates.FLOOR)
        return

    try:
        user_data[uid]["rooms"] = int(text)
    except Exception:
        await message.answer("Количество комнат должно быть числом. Введите цифрами.", keyboard=kb_for_state_inline(RentStates.ROOMS))
        return

    if await maybe_back_to_preview(message, uid):
        return

    await bot.state_dispenser.set(peer, RentStates.PRICE)
    await prompt_for_state(message, RentStates.PRICE)

# ---------------------------
# PRICE
# ---------------------------
@bot.on.message(state=RentStates.PRICE)
async def price_handler(message: Message):
    uid = str(message.from_id)
    peer = message.peer_id
    text = (message.text or "").strip()
    user_data.setdefault(uid, {})

    if text == "Меню":
        await bot.state_dispenser.delete(peer)
        await message.answer("Вы вернулись в меню.", keyboard=main_menu_inline())
        return
    if text == "Назад":
        await bot.state_dispenser.set(peer, RentStates.ROOMS)
        await prompt_for_state(message, RentStates.ROOMS)
        return

    try:
        user_data[uid]["price"] = int(text)
    except Exception:
        await message.answer("Цена должна быть числом. Введите цифрами.", keyboard=kb_for_state_inline(RentStates.PRICE))
        return

    if await maybe_back_to_preview(message, uid):
        return

    await bot.state_dispenser.set(peer, RentStates.DESCRIPTION)
    await prompt_for_state(message, RentStates.DESCRIPTION)

# ---------------------------
# DESCRIPTION -> PHOTOS
# ---------------------------
@bot.on.message(state=RentStates.DESCRIPTION)
async def description_handler(message: Message):
    uid = str(message.from_id)
    peer = message.peer_id
    text = (message.text or "").strip()
    user_data.setdefault(uid, {})

    if text == "Меню":
        await bot.state_dispenser.delete(peer)
        await message.answer("Вы вернулись в меню.", keyboard=main_menu_inline())
        return
    if text == "Назад":
        await bot.state_dispenser.set(peer, RentStates.PRICE)
        await prompt_for_state(message, RentStates.PRICE)
        return

    user_data[uid]["description"] = message.text
    # Next step: photos
    await bot.state_dispenser.set(peer, RentStates.PHOTOS)
    await message.answer(STATE_PROMPTS.get(RentStates.PHOTOS, "Прикрепите фото или Пропустить."), keyboard=kb_photos_inline())

# ---------------------------
# PHOTOS (accept photo attachments, "Готово"/"Пропустить")
# ---------------------------
@bot.on.message(state=RentStates.PHOTOS)
async def photos_handler(message: Message):
    uid = str(message.from_id)
    peer = message.peer_id
    text = (message.text or "").strip()
    user_data.setdefault(uid, {})

    # Buttons
    if text == "Меню":
        await bot.state_dispenser.delete(peer)
        await message.answer("Вы вернулись в меню.", keyboard=main_menu_inline())
        return
    if text == "Назад":
        await bot.state_dispenser.set(peer, RentStates.DESCRIPTION)
        await prompt_for_state(message, RentStates.DESCRIPTION)
        return
    if text in ("Пропустить", "Готово"):
        await bot.state_dispenser.set(peer, RentStates.FIO)
        await prompt_for_state(message, RentStates.FIO)
        return

    # If attachments contain photos - extract and store
    photo_urls = extract_photo_urls_from_message(message)
    if photo_urls:
        user_data[uid].setdefault("photo_urls", []).extend(photo_urls)
        cnt = len(user_data[uid]["photo_urls"])
        await message.answer(f"Добавлено {len(photo_urls)} фото. Всего: {cnt}. Отправьте ещё или нажмите «Готово»/«Пропустить».", keyboard=kb_photos_inline())
        return

    # otherwise prompt user
    await message.answer("Пожалуйста, пришлите фото (файл) или нажмите «Пропустить»/«Готово».", keyboard=kb_photos_inline())

# ---------------------------
# FIO
# ---------------------------
@bot.on.message(state=RentStates.FIO)
async def fio_handler(message: Message):
    uid = str(message.from_id)
    peer = message.peer_id
    text = (message.text or "").strip()
    user_data.setdefault(uid, {})

    if text == "Меню":
        await bot.state_dispenser.delete(peer)
        await message.answer("Вы вернулись в меню.", keyboard=main_menu_inline())
        return
    if text == "Назад":
        await bot.state_dispenser.set(peer, RentStates.PHOTOS)
        await message.answer(STATE_PROMPTS.get(RentStates.PHOTOS, "Прикрепите фото или Пропустить."), keyboard=kb_photos_inline())
        return

    if not text or len(text) < 2:
        await message.answer("Пожалуйста, укажите ФИО (имя и фамилия).", keyboard=kb_for_state_inline(RentStates.FIO))
        return

    user_data[uid]["fio"] = text
    await bot.state_dispenser.set(peer, RentStates.PHONE)
    await prompt_for_state(message, RentStates.PHONE)

# ---------------------------
# PHONE
# ---------------------------
@bot.on.message(state=RentStates.PHONE)
async def phone_handler(message: Message):
    uid = str(message.from_id)
    peer = message.peer_id
    text = (message.text or "").strip()
    user_data.setdefault(uid, {})

    if text == "Меню":
        await bot.state_dispenser.delete(peer)
        await message.answer("Вы вернулись в меню.", keyboard=main_menu_inline())
        return
    if text == "Назад":
        await bot.state_dispenser.set(peer, RentStates.FIO)
        await prompt_for_state(message, RentStates.FIO)
        return

    normalized = re.sub(r"[^\d+]", "", text)
    if normalized.count("+") > 1:
        normalized = normalized.replace("+", "")
        normalized = "+" + normalized
    digits = re.sub(r"\D", "", normalized)
    if len(digits) < 7:
        await message.answer("Неверный номер — должно быть не менее 7 цифр. Попробуйте ещё раз.", keyboard=kb_for_state_inline(RentStates.PHONE))
        return

    user_data[uid]["phone"] = normalized

    # show preview
    draft = user_data[uid]
    preview_text = (
        f"📌 Предпросмотр объявления:\n\n"
        f"🏙 Район: {draft.get('district','—')}\n"
        f"📍 Адрес: {draft.get('address','—')}\n"
        f"🏢 Этаж: {draft.get('floor','—')}\n"
        f"🚪 Комнат: {draft.get('rooms','—')}\n"
        f"💰 Цена: {draft.get('price','—')}\n"
        f"📝 Описание:\n{draft.get('description','—')}\n\n"
        f"👤 Контакт: {draft.get('fio','—')}\n"
        f"📞 Телефон: {draft.get('phone','—')}\n\n"
        "Нажмите «Отправить в отложенные», чтобы поставить объявление в отложенные записи сообщества, "
        "или выберите «Изменить ...», чтобы редактировать поле."
    )
    await bot.state_dispenser.set(peer, RentStates.PREVIEW)
    await message.answer(preview_text, keyboard=kb_preview_inline(draft))

# ---------------------------
# Preview actions: Send and Edit buttons
# ---------------------------
@bot.on.message(text="Отправить в отложенные")
async def send_scheduled_handler(message: Message):
    uid = str(message.from_id)
    peer = message.peer_id
    draft = user_data.get(uid)
    if not draft:
        await message.answer("Нет черновика для отправки.", keyboard=main_menu_inline())
        return

    text = build_text_from_draft(draft)
    if not isinstance(text, str):
        text = str(text)

    attachments: Optional[str] = None
    photo_urls = draft.get("photo_urls") or []
    if photo_urls:
        await message.answer("Начинаю загрузку фото в сообщество... (это может занять некоторое время)")
        upload_resp = upload_photos_to_group(photo_urls)
        if "error" in upload_resp:
            err = upload_resp.get("error", {})
            await message.answer(f"Ошибка при загрузке фото: {err.get('error_msg')}", keyboard=main_menu_inline())
            return
        attachments = upload_resp.get("response", {}).get("attachments")

    try:
        resp = send_to_scheduled(text=text, attachments=attachments, delay_seconds=300)
    except Exception as e:
        await message.answer(f"Ошибка при отправке: {e}", keyboard=main_menu_inline())
        return

    if "error" in resp:
        err = resp.get("error", {})
        await message.answer(f"Ошибка при отправке в отложенные: {err.get('error_msg')}", keyboard=main_menu_inline())
        return

    post_id = resp.get("response", {}).get("post_id")
    if post_id:
        await message.answer(
            f"Готово — объявление отправлено в отложенные. post_id={post_id}\n"
            f"Фото прикреплены автоматически (если загрузка прошла успешно).",
            keyboard=main_menu_inline()
        )
    else:
        await message.answer("Готово — объявление отправлено в отложенные. Проверьте админку сообщества.", keyboard=main_menu_inline())

    # clear draft and state
    user_data.pop(uid, None)
    await bot.state_dispenser.delete(peer)

# ---------------------------
# Edit handlers (from preview)
# ---------------------------
@bot.on.message(text="Изменить район")
async def edit_district(message: Message):
    uid = str(message.from_id)
    user_data.setdefault(uid, {})["back_to_preview"] = True
    await bot.state_dispenser.set(message.peer_id, RentStates.DISTRICT)
    await message.answer(STATE_PROMPTS[RentStates.DISTRICT], keyboard=kb_for_state_inline(RentStates.DISTRICT))

@bot.on.message(text="Изменить адрес")
async def edit_address(message: Message):
    uid = str(message.from_id)
    user_data.setdefault(uid, {})["back_to_preview"] = True
    await bot.state_dispenser.set(message.peer_id, RentStates.ADDRESS)
    await prompt_for_state(message, RentStates.ADDRESS)

@bot.on.message(text="Изменить этаж")
async def edit_floor(message: Message):
    uid = str(message.from_id)
    user_data.setdefault(uid, {})["back_to_preview"] = True
    await bot.state_dispenser.set(message.peer_id, RentStates.FLOOR)
    await prompt_for_state(message, RentStates.FLOOR)

@bot.on.message(text="Изменить комнат")
async def edit_rooms(message: Message):
    uid = str(message.from_id)
    user_data.setdefault(uid, {})["back_to_preview"] = True
    await bot.state_dispenser.set(message.peer_id, RentStates.ROOMS)
    await prompt_for_state(message, RentStates.ROOMS)

@bot.on.message(text="Изменить цену")
async def edit_price(message: Message):
    uid = str(message.from_id)
    user_data.setdefault(uid, {})["back_to_preview"] = True
    await bot.state_dispenser.set(message.peer_id, RentStates.PRICE)
    await prompt_for_state(message, RentStates.PRICE)

@bot.on.message(text="Изменить описание")
async def edit_description(message: Message):
    uid = str(message.from_id)
    user_data.setdefault(uid, {})["back_to_preview"] = True
    await bot.state_dispenser.set(message.peer_id, RentStates.DESCRIPTION)
    await prompt_for_state(message, RentStates.DESCRIPTION)

@bot.on.message(text="Изменить ФИО")
async def edit_fio(message: Message):
    uid = str(message.from_id)
    user_data.setdefault(uid, {})["back_to_preview"] = True
    await bot.state_dispenser.set(message.peer_id, RentStates.FIO)
    await prompt_for_state(message, RentStates.FIO)

@bot.on.message(text="Изменить телефон")
async def edit_phone(message: Message):
    uid = str(message.from_id)
    user_data.setdefault(uid, {})["back_to_preview"] = True
    await bot.state_dispenser.set(message.peer_id, RentStates.PHONE)
    await prompt_for_state(message, RentStates.PHONE)

# ---------------------------
# Fallback global handlers (optional)
# ---------------------------
@bot.on.message(text=["Назад", "Меню"])
async def global_back_or_menu(message: Message):
    text = (message.text or "").strip()
    peer = message.peer_id
    if text == "Меню":
        await bot.state_dispenser.delete(peer)
        await message.answer("Вы вернулись в меню.", keyboard=main_menu_inline())
        return
    await bot.state_dispenser.delete(peer)
    await message.answer("Вы вернулись в меню.", keyboard=main_menu_inline())
