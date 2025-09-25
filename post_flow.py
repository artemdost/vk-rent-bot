# post_flow.py
from core import bot, user_data, RentStates, main_menu_inline, kb_for_state_inline, kb_preview_inline, prompt_for_state
from post_submit import send_to_scheduled, build_text_from_draft

from vkbottle.bot import Message

# --- Старт и меню ---
@bot.on.message(text="/start")
async def start_command(message: Message):
    await message.answer("Привет! Выберите действие:", keyboard=main_menu_inline())

@bot.on.message(text="Посмотреть объявления")
async def view_rents(message: Message):
    await message.answer("Список объявлений пока не реализован.", keyboard=main_menu_inline())

@bot.on.message(text="Выложить объявление")
async def post_rent(message: Message):
    uid = str(message.from_id)
    user_data[uid] = {}
    await bot.state_dispenser.set(message.peer_id, RentStates.DISTRICT)
    await message.answer("Выберите район:", keyboard=kb_for_state_inline(RentStates.DISTRICT))

# --- DISTRICT ---
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

# --- ADDRESS ---
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
        await message.answer("Выберите район:", keyboard=kb_for_state_inline(RentStates.DISTRICT))
        return

    # save
    user_data[uid]["address"] = message.text
    await bot.state_dispenser.set(peer, RentStates.FLOOR)
    await prompt_for_state(message, RentStates.FLOOR)

# --- FLOOR ---
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
    except:
        await message.answer("Этаж должен быть числом. Введите цифрами.", keyboard=kb_for_state_inline(RentStates.FLOOR))
        return

    await bot.state_dispenser.set(peer, RentStates.ROOMS)
    await prompt_for_state(message, RentStates.ROOMS)

# --- ROOMS ---
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
    except:
        await message.answer("Количество комнат должно быть числом. Введите цифрами.", keyboard=kb_for_state_inline(RentStates.ROOMS))
        return

    await bot.state_dispenser.set(peer, RentStates.PRICE)
    await prompt_for_state(message, RentStates.PRICE)

# --- PRICE ---
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
    except:
        await message.answer("Цена должна быть числом. Введите цифрами.", keyboard=kb_for_state_inline(RentStates.PRICE))
        return

    await bot.state_dispenser.set(peer, RentStates.DESCRIPTION)
    await prompt_for_state(message, RentStates.DESCRIPTION)

# --- DESCRIPTION -> preview ---
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

    # show preview
    draft = user_data[uid]
    preview = (
        f"📌 Предпросмотр объявления:\n\n"
        f"🏙 Район: {draft.get('district','—')}\n"
        f"📍 Адрес: {draft.get('address','—')}\n"
        f"🏢 Этаж: {draft.get('floor','—')}\n"
        f"🚪 Комнат: {draft.get('rooms','—')}\n"
        f"💰 Цена: {draft.get('price','—')}\n"
        f"📝 Описание:\n{draft.get('description','—')}\n\n"
        "Нажмите «Отправить в отложенные», чтобы поставить объявление в отложенные записи сообщества, "
        "или выберите «Изменить ...», чтобы редактировать поле."
    )
    await bot.state_dispenser.set(peer, RentStates.PREVIEW)
    await message.answer(preview, keyboard=kb_preview_inline(draft))

# --- Preview buttons: Edit / Send ---
@bot.on.message(text="Отправить в отложенные")
async def send_scheduled_handler(message: Message):
    uid = str(message.from_id)
    peer = message.peer_id
    draft = user_data.get(uid)
    if not draft:
        await message.answer("Нет черновика для отправки.", keyboard=main_menu_inline())
        return

    text = build_text_from_draft(draft)
    # delay_seconds: сколько в будущем поставить publish_date (300s = 5мин)
    resp = send_to_scheduled(text=text, attachments=None, delay_seconds=300)

    if "error" in resp:
        err = resp.get("error", {})
        await message.answer(f"Ошибка при отправке в отложенные: {err.get('error_msg')}", keyboard=main_menu_inline())
        return

    post_id = resp.get("response", {}).get("post_id")
    await message.answer(f"Готово — объявление отправлено в отложенные. post_id={post_id}", keyboard=main_menu_inline())
    user_data.pop(uid, None)
    await bot.state_dispenser.delete(peer)

# edit handlers from preview
@bot.on.message(text="Изменить район")
async def edit_district(message: Message):
    uid = str(message.from_id)
    user_data.setdefault(uid, {})["back_to_preview"] = True
    await bot.state_dispenser.set(message.peer_id, RentStates.DISTRICT)
    await message.answer("Выберите район:", keyboard=kb_for_state_inline(RentStates.DISTRICT))

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
async def edit_desc(message: Message):
    uid = str(message.from_id)
    user_data.setdefault(uid, {})["back_to_preview"] = True
    await bot.state_dispenser.set(message.peer_id, RentStates.DESCRIPTION)
    await prompt_for_state(message, RentStates.DESCRIPTION)

# catch edits: if user had back_to_preview flag, after saving we return to preview

# IMPORTANT: to ensure edit->preview flow works, we intercept changes in each state handler above
# We already set "back_to_preview" flag when user clicked edit; now we must, in each state handler,
# after saving new value, check flag and return to preview instead of moving forward.
# For simplicity, we handle that inside those handlers (see examples in DESCRIPTION/FLOOR/etc.)
# (Handlers above for ADDRESS/FLOOR/ROOMS/PRICE check nothing about back_to_preview; we need to modify them:)
# Minimal approach: re-check flag in prompt_for_state / after saving — but to keep file short, we do a quick helper here.

# small utility to check and return to preview if needed
async def maybe_back_to_preview(message: Message, uid: str):
    # if user had requested edit from preview, go back to preview after they input new value
    if user_data.get(uid, {}).pop("back_to_preview", False):
        draft = user_data.get(uid, {})
        preview = (
            f"📌 Обновлённый предпросмотр:\n\n"
            f"🏙 Район: {draft.get('district','—')}\n"
            f"📍 Адрес: {draft.get('address','—')}\n"
            f"🏢 Этаж: {draft.get('floor','—')}\n"
            f"🚪 Комнат: {draft.get('rooms','—')}\n"
            f"💰 Цена: {draft.get('price','—')}\n"
            f"📝 Описание:\n{draft.get('description','—')}\n\n"
            "Нажмите «Отправить в отложенные» или продолжите редактирование."
        )
        await bot.state_dispenser.set(message.peer_id, RentStates.PREVIEW)
        await message.answer(preview, keyboard=kb_preview_inline(draft))
        return True
    return False

# integrate maybe_back_to_preview checks into the handlers where user input is saved:
# modify those handlers to call maybe_back_to_preview after saving. For brevity, we'll patch them inline:
# (We will re-define the ADDRESS/FLOOR/ROOMS/PRICE/DESCRIPTION handlers in a compact way to include the check.)

# Re-define ADDRESS with back->preview handling:
@bot.on.message(state=RentStates.ADDRESS)
async def address_handler2(message: Message):
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
        await message.answer("Выберите район:", keyboard=kb_for_state_inline(RentStates.DISTRICT))
        return

    user_data[uid]["address"] = message.text

    # if this was an edit from preview -> back to preview
    if await maybe_back_to_preview(message, uid):
        return

    await bot.state_dispenser.set(peer, RentStates.FLOOR)
    await prompt_for_state(message, RentStates.FLOOR)

# Re-define FLOOR with back->preview handling:
@bot.on.message(state=RentStates.FLOOR)
async def floor_handler2(message: Message):
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
    except:
        await message.answer("Этаж должен быть числом. Введите цифрами.", keyboard=kb_for_state_inline(RentStates.FLOOR))
        return

    if await maybe_back_to_preview(message, uid):
        return

    await bot.state_dispenser.set(peer, RentStates.ROOMS)
    await prompt_for_state(message, RentStates.ROOMS)

@bot.on.message(state=RentStates.ROOMS)
async def rooms_handler2(message: Message):
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
    except:
        await message.answer("Количество комнат должно быть числом. Введите цифрами.", keyboard=kb_for_state_inline(RentStates.ROOMS))
        return

    if await maybe_back_to_preview(message, uid):
        return

    await bot.state_dispenser.set(peer, RentStates.PRICE)
    await prompt_for_state(message, RentStates.PRICE)

@bot.on.message(state=RentStates.PRICE)
async def price_handler2(message: Message):
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
    except:
        await message.answer("Цена должна быть числом. Введите цифрами.", keyboard=kb_for_state_inline(RentStates.PRICE))
        return

    if await maybe_back_to_preview(message, uid):
        return

    await bot.state_dispenser.set(peer, RentStates.DESCRIPTION)
    await prompt_for_state(message, RentStates.DESCRIPTION)

# DESCRIPTION already defined above — we'll rely on that one which shows preview and respects edits.

# end of post_flow.py
