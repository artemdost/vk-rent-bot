# post_flow.py

# добавьте в начало файла
import os
import time
import requests

API_V = os.getenv("VK_API_VERSION", "5.199")
GROUP_ID = int(os.getenv("GROUP_ID", "0"))
GROUP_TOKEN = os.getenv("GROUP_TOKEN")  # токен сообщества (обязательно)

def send_post_to_scheduled(group_token: str, group_id: int, text: str, attachments: str = None, delay_seconds: int = 3600):
    """
    Отправляет пост от имени сообщества в отложенные (publish_date = now + delay_seconds).
    - group_token: токен сообщества с правом wall
    - group_id: положительный id группы
    - text: текст поста
    - attachments: строка вида "photo<owner>_<id>,doc..." (опционально)
    - delay_seconds: сколько секунд от текущего времени поставить publish_date (по умолчанию 1 час)
    Возвращает dict (ответ VK API).
    """
    if not group_token:
        return {"error": {"error_msg": "GROUP_TOKEN не задан"}}

    owner_id = -abs(int(group_id))
    publish_date = int(time.time()) + int(delay_seconds)
    params = {
        "access_token": group_token,
        "owner_id": owner_id,
        "from_group": 1,
        "message": text,
        "publish_date": publish_date,
        "v": API_V,
    }
    if attachments:
        params["attachments"] = attachments

    try:
        r = requests.post("https://api.vk.com/method/wall.post", data=params, timeout=15)
        return r.json()
    except Exception as e:
        return {"error": {"error_msg": str(e)}}


from core import (
    bot,
    RentStates,
    user_data,
    prompt_for_state,
    STATE_PROMPTS,
    normalize_state_name,
    kb_for_state_inline,
    kb_preview_inline,
    published_ads,
    main_menu_inline,      # <- обязательно импортируем
)

# helper: собрать и показать preview для данного user
async def show_preview(message, uid):
    peer = message.peer_id
    data = user_data.get(uid, {})
    preview = (
        f"📌 Предпросмотр объявления:\n\n"
        f"🏙 Район: {data.get('district','—')}\n"
        f"📍 Адрес: {data.get('address','—')}\n"
        f"🏢 Этаж: {data.get('floor','—')}\n"
        f"🚪 Комнат: {data.get('rooms','—')}\n"
        f"💰 Цена: {data.get('price','—')}\n"
        f"📝 Описание: {data.get('description','—')}\n\n"
        f"Нажмите «Разместить», чтобы отправить объявление в предложения, или выберите поле, чтобы отредактировать."
    )
    # ставим PREVIEW state
    await bot.state_dispenser.set(peer, RentStates.PREVIEW)
    # очистим флаг (вдруг он ещё был)
    user_data.setdefault(uid, {}).pop("back_to_preview", None)
    await message.answer(preview, keyboard=kb_preview_inline())


# старт публикации (вызывается из main)
async def start_posting(message):
    uid = str(message.from_id)
    user_data.setdefault(uid, {})
    await bot.state_dispenser.set(message.peer_id, RentStates.DISTRICT)
    await message.answer(STATE_PROMPTS["district"], keyboard=kb_for_state_inline(RentStates.DISTRICT))


# ------------------ state handlers ------------------

@bot.on.message(state=RentStates.DISTRICT)
async def district_handler(message):
    uid = str(message.from_id)
    peer = message.peer_id
    text = (message.text or "").strip()
    user_data.setdefault(uid, {})

    if text == "Меню":
        # отмена — возвращаем в меню и чистим флаг
        await bot.state_dispenser.delete(peer)
        user_data.get(uid, {}).pop("back_to_preview", None)
        await message.answer("Вы вернулись в меню.", keyboard=main_menu_inline())
        return

    valid = {"Центр", "Север", "Юг", "Восток", "Запад"}
    if text not in valid:
        await message.answer("Пожалуйста, выберите район из кнопок.", keyboard=kb_for_state_inline(RentStates.DISTRICT))
        return

    user_data[uid]["district"] = text

    # если это редактирование из предпросмотра — сразу возвращаем к preview
    if user_data[uid].pop("back_to_preview", False):
        await show_preview(message, uid)
        return

    # иначе — обычный flow: идём к адресу
    await bot.state_dispenser.set(peer, RentStates.ADDRESS)
    await prompt_for_state(message, RentStates.ADDRESS, inline=True)


@bot.on.message(state=RentStates.ADDRESS)
async def address_handler(message):
    uid = str(message.from_id)
    peer = message.peer_id
    user_data.setdefault(uid, {})
    user_data[uid]["address"] = message.text

    if user_data[uid].pop("back_to_preview", False):
        await show_preview(message, uid)
        return

    await bot.state_dispenser.set(peer, RentStates.FLOOR)
    await prompt_for_state(message, RentStates.FLOOR, inline=True)


@bot.on.message(state=RentStates.FLOOR)
async def floor_handler(message):
    uid = str(message.from_id)
    peer = message.peer_id
    user_data.setdefault(uid, {})
    text = (message.text or "").strip()
    try:
        user_data[uid]["floor"] = int(text)
    except:
        await message.answer("Этаж должен быть числом. Введите цифрами.", keyboard=kb_for_state_inline(RentStates.FLOOR))
        return

    if user_data[uid].pop("back_to_preview", False):
        await show_preview(message, uid)
        return

    await bot.state_dispenser.set(peer, RentStates.ROOMS)
    await prompt_for_state(message, RentStates.ROOMS, inline=True)


@bot.on.message(state=RentStates.ROOMS)
async def rooms_handler(message):
    uid = str(message.from_id)
    peer = message.peer_id
    user_data.setdefault(uid, {})
    text = (message.text or "").strip()
    try:
        user_data[uid]["rooms"] = int(text)
    except:
        await message.answer("Количество комнат должно быть числом. Введите цифрами.", keyboard=kb_for_state_inline(RentStates.ROOMS))
        return

    if user_data[uid].pop("back_to_preview", False):
        await show_preview(message, uid)
        return

    await bot.state_dispenser.set(peer, RentStates.PRICE)
    await prompt_for_state(message, RentStates.PRICE, inline=True)


@bot.on.message(state=RentStates.PRICE)
async def price_handler(message):
    uid = str(message.from_id)
    peer = message.peer_id
    user_data.setdefault(uid, {})
    text = (message.text or "").strip()
    try:
        user_data[uid]["price"] = int(text)
    except:
        await message.answer("Цена должна быть числом. Введите цифрами.", keyboard=kb_for_state_inline(RentStates.PRICE))
        return

    if user_data[uid].pop("back_to_preview", False):
        await show_preview(message, uid)
        return

    await bot.state_dispenser.set(peer, RentStates.DESCRIPTION)
    await prompt_for_state(message, RentStates.DESCRIPTION, inline=True)


@bot.on.message(state=RentStates.DESCRIPTION)
async def description_handler(message):
    uid = str(message.from_id)
    peer = message.peer_id
    user_data.setdefault(uid, {})
    user_data[uid]["description"] = message.text

    # Если пришли сюда в режиме редактирования (back_to_preview) — показать preview
    if user_data[uid].pop("back_to_preview", False):
        await show_preview(message, uid)
        return

    # обычный flow (создание нового объявления) — показать preview
    await show_preview(message, uid)


# ------------------ preview handlers ------------------

@bot.on.message(text="Разместить")
async def publish_handler(message):
    uid = str(message.from_id)
    peer = message.peer_id
    current = await bot.state_dispenser.get(peer)
    # допускаем публикацию как из PREVIEW, так и если черновик есть
    if (current and normalize_state_name(current) != "preview") and uid not in user_data:
        await message.answer("Нет черновика для публикации.", keyboard=main_menu_inline())
        return

    ad = user_data.get(uid, {}).copy()
    ad["author_id"] = uid
    published_ads.append(ad)  # здесь заменишь на реальную публикацию
    await message.answer("✅ Объявление размещено в предложках. Спасибо!", keyboard=main_menu_inline())

    # очистка
    await bot.state_dispenser.delete(peer)
    user_data.pop(uid, None)


# ---- edit buttons: ставим back_to_preview и переводим на шаг ----

@bot.on.message(text="Изменить район")
async def edit_district_handler(message):
    uid = str(message.from_id)
    user_data.setdefault(uid, {})["back_to_preview"] = True
    await bot.state_dispenser.set(message.peer_id, RentStates.DISTRICT)
    await prompt_for_state(message, RentStates.DISTRICT, inline=True)

@bot.on.message(text="Изменить адрес")
async def edit_address_handler(message):
    uid = str(message.from_id)
    user_data.setdefault(uid, {})["back_to_preview"] = True
    await bot.state_dispenser.set(message.peer_id, RentStates.ADDRESS)
    await prompt_for_state(message, RentStates.ADDRESS, inline=True)

@bot.on.message(text="Изменить этаж")
async def edit_floor_handler(message):
    uid = str(message.from_id)
    user_data.setdefault(uid, {})["back_to_preview"] = True
    await bot.state_dispenser.set(message.peer_id, RentStates.FLOOR)
    await prompt_for_state(message, RentStates.FLOOR, inline=True)

@bot.on.message(text="Изменить комнат")
async def edit_rooms_handler(message):
    uid = str(message.from_id)
    user_data.setdefault(uid, {})["back_to_preview"] = True
    await bot.state_dispenser.set(message.peer_id, RentStates.ROOMS)
    await prompt_for_state(message, RentStates.ROOMS, inline=True)

@bot.on.message(text="Изменить цену")
async def edit_price_handler(message):
    uid = str(message.from_id)
    user_data.setdefault(uid, {})["back_to_preview"] = True
    await bot.state_dispenser.set(message.peer_id, RentStates.PRICE)
    await prompt_for_state(message, RentStates.PRICE, inline=True)

@bot.on.message(text="Изменить описание")
async def edit_description_handler(message):
    uid = str(message.from_id)
    user_data.setdefault(uid, {})["back_to_preview"] = True
    await bot.state_dispenser.set(message.peer_id, RentStates.DESCRIPTION)
    await prompt_for_state(message, RentStates.DESCRIPTION, inline=True)

# в пост-флоу, где у вас есть user_data и draft/preview
@bot.on.message(text="Отправить в отложенные")
async def send_to_scheduled_handler(message):
    uid = str(message.from_id)
    peer = message.peer_id
    draft = user_data.get(uid)
    if not draft:
        await message.answer("Нет черновика для отправки.", keyboard=main_menu_inline())
        return

    if GROUP_ID == 0 or not GROUP_TOKEN:
        await message.answer(
            "GROUP_ID или GROUP_TOKEN не настроены на сервере. Добавь в .env:\nGROUP_ID и GROUP_TOKEN (токен сообщества с правом wall).",
            keyboard=main_menu_inline()
        )
        return

    # соберём текст (у тебя есть функция build_preview_text_for_sending)
    text = (
        f"🏙 Район: {draft.get('district','')}\n"
        f"📍 Адрес: {draft.get('address','')}\n"
        f"🏢 Этаж: {draft.get('floor','')}\n"
        f"🚪 Комнат: {draft.get('rooms','')}\n"
        f"💰 Цена: {draft.get('price','')}\n\n"
        f"{draft.get('description','')}"
    )

    # delay_seconds: можно ставить небольшую задержку, например 60 или 3600.
    # VK будет считать publish_date>now => пост окажется в "Отложенные записи".
    resp = send_post_to_scheduled(GROUP_TOKEN, GROUP_ID, text, attachments=None, delay_seconds=3600)

    if "error" in resp:
        # аккуратно показать сообщение об ошибке
        err = resp.get("error", {})
        msg = err.get("error_msg") or str(err)
        await message.answer(f"Ошибка при отправке в отложенные: {msg}", keyboard=main_menu_inline())
        # можно логировать resp для отладки
        print("VK send scheduled error:", resp)
        return

    # успешно — resp['response']['post_id'] обычно содержит id (если вернулся)
    await message.answer("Готово — объявление отправлено в Отложенные записи сообщества.", keyboard=main_menu_inline())
    # очистим черновик (или пометим как отправлен)
    user_data.pop(uid, None)

