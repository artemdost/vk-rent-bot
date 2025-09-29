# post_flow.py
import json
import random
import time
import re
import os
from typing import List, Dict, Any, Optional, Tuple

import requests
from vkbottle import Keyboard, KeyboardButtonColor, Text, GroupEventType, GroupTypes
from vkbottle.bot import Message
from core import (
    bot,
    user_data,
    RentStates,
    SearchStates,
    main_menu_inline,
    kb_for_state_inline,
    kb_preview_inline,
    kb_photos_inline,
    prompt_for_state,
    STATE_PROMPTS,
    TOKEN_FOR_BOT,
    GROUP_ID,
    API_V,
    USER_TOKEN,
)
from post_submit import (
    send_to_scheduled,
    build_text_from_draft,
    upload_photos_to_group,
    UPLOAD_TOKEN,
    format_price_display,
    DEFAULT_SCHEDULE_DELAY,
)

MENU_GREETING = "Привет! Выберите действие:"
START_COMMANDS = {"/start", "start", "начать", "старт"}
SEARCH_RESULTS_LIMIT = int(os.getenv("SEARCH_RESULTS_LIMIT", "30"))

ALLOW_GREETING_SUPPRESS_SECONDS = 5.0
_recent_allow_greetings: Dict[int, float] = {}

def _cleanup_recent_allow(now: float) -> None:
    stale = [uid for uid, mark in _recent_allow_greetings.items() if now - mark > ALLOW_GREETING_SUPPRESS_SECONDS]
    for uid in stale:
        _recent_allow_greetings.pop(uid, None)

def _mark_allow_greeting(user_id: int) -> None:
    now = time.monotonic()
    _recent_allow_greetings[user_id] = now
    _cleanup_recent_allow(now)

def _allow_greeted_recently(user_id: int) -> bool:
    now = time.monotonic()
    ts = _recent_allow_greetings.pop(user_id, None)
    _cleanup_recent_allow(now)
    return ts is not None and now - ts <= ALLOW_GREETING_SUPPRESS_SECONDS

def _random_id() -> int:
    return random.randint(-2_147_483_648, 2_147_483_647)

def state_keyboard(uid: str, state) -> str:
    editing = bool(user_data.get(uid, {}).get("back_to_preview"))
    return kb_for_state_inline(state, editing=editing)

def photos_keyboard(uid: str) -> str:
    editing = bool(user_data.get(uid, {}).get("back_to_preview"))
    return kb_photos_inline(editing=editing)

# ---------------------------
# Utility helpers
# ---------------------------
async def extract_photo_urls_from_message(message: Message) -> List[str]:
    """Извлекаем URL всех фото из сообщения, запрашивая полную версию при необходимости."""

    try:
        full_msg = await message.get_full_message()
    except Exception:
        full_msg = None

    candidate_sources = []
    if full_msg and getattr(full_msg, "attachments", None):
        candidate_sources.append(full_msg.attachments)
    if getattr(message, "attachments", None):
        candidate_sources.append(message.attachments)
    if full_msg:
        raw_atts = getattr(full_msg, "__dict__", {}).get("attachments")
        if raw_atts and raw_atts not in candidate_sources:
            candidate_sources.append(raw_atts)
    raw_current = getattr(message, "__dict__", {}).get("attachments")
    if raw_current and raw_current not in candidate_sources:
        candidate_sources.append(raw_current)
    raw_payload = getattr(message, "dict", None)
    if callable(raw_payload):
        try:
            attachments_dict = raw_payload().get("attachments")
            if attachments_dict and attachments_dict not in candidate_sources:
                candidate_sources.append(attachments_dict)
        except Exception:
            pass

    urls: List[str] = []
    seen: set = set()
    for source in candidate_sources:
        items = list(source or [])
        for a in items:
            try:
                photo = getattr(a, "photo", None)
                if photo is None and isinstance(a, dict):
                    photo = a.get("photo")
                if not photo:
                    continue
                if hasattr(photo, "model_dump"):
                    photo_data = photo.model_dump()
                elif isinstance(photo, dict):
                    photo_data = photo
                else:
                    photo_data = {
                        key: getattr(photo, key)
                        for key in dir(photo)
                        if not key.startswith("_")
                    }

                added = False
                size_candidates = photo_data.get("sizes") or []
                if size_candidates:
                    if isinstance(size_candidates, dict):
                        size_candidates = size_candidates.values()
                    for size in list(size_candidates)[::-1]:
                        if isinstance(size, dict):
                            url = size.get("url")
                        else:
                            url = getattr(size, "url", None)
                        if url:
                            if url not in seen:
                                urls.append(url)
                                seen.add(url)
                            added = True
                            break
                if not added:
                    for key, value in photo_data.items():
                        if isinstance(value, str) and value.startswith("http"):
                            if value not in seen:
                                urls.append(value)
                                seen.add(value)
                            added = True
                            break
            except Exception:
                continue

    return urls

async def maybe_back_to_preview(message: Message, uid: str) -> bool:
    """
    Если установлен флаг back_to_preview — показываем обновлённый превью и возвращаем True.
    """
    if user_data.get(uid, {}).pop("back_to_preview", False):
        draft = user_data.get(uid, {})
        price_formatted = format_price_display(draft.get("price"))
        preview_text = (
            f"📌 Обновлённый предпросмотр:\n\n"
            f"💰 Цена: {price_formatted}\n"
            f"🏙 Район: {draft.get('district','—')}\n"
            f"📍 Адрес: {draft.get('address','—')}\n"
            f"🏢 Этаж: {draft.get('floor','—')}\n"
            f"🚪 Комнат: {draft.get('rooms','—')}\n"
            f"📝 Описание:\n{draft.get('description','—')}\n\n"
            f"👤 Контакт: {draft.get('fio','—')}\n"
            f"📞 Телефон: {draft.get('phone','—')}\n\n"
            "Нажмите «Отправить» или продолжите редактирование."
        )
        await bot.state_dispenser.set(message.peer_id, RentStates.PREVIEW)
        await message.answer(preview_text, keyboard=kb_preview_inline(draft))
        return True
    return False

# ---------------------------
# Search flow helpers/data
# ---------------------------
SEARCH_PROMPTS = {
    SearchStates.DISTRICT: "Выберите район или нажмите «Любой»:",
    SearchStates.PRICE_MIN: "Укажите минимальную цену",
    SearchStates.PRICE_MAX: "Укажите максимальную цену",
    SearchStates.ROOMS: "Сколько комнат вас интересует?",
    SearchStates.RECENT_DAYS: "Показать объявления за 7 дней, за 30 дней или без ограничения?",
}

search_sessions: Dict[str, Dict[str, Any]] = {}


def search_kb_for_state_inline(state) -> str:
    if state == SearchStates.DISTRICT:
        kb = Keyboard(inline=True)
        kb.add(Text("Автозаводский"), color=KeyboardButtonColor.PRIMARY)
        kb.add(Text("Канавинский"), color=KeyboardButtonColor.PRIMARY)
        kb.row()
        kb.add(Text("Ленинский"), color=KeyboardButtonColor.PRIMARY)
        kb.add(Text("Московский"), color=KeyboardButtonColor.PRIMARY)
        kb.row()
        kb.add(Text("Нижегородский"), color=KeyboardButtonColor.PRIMARY)
        kb.add(Text("Приокский"), color=KeyboardButtonColor.PRIMARY)
        kb.row()
        kb.add(Text("Советский"), color=KeyboardButtonColor.PRIMARY)
        kb.add(Text("Сормовский"), color=KeyboardButtonColor.PRIMARY)
        kb.row()
        kb.add(Text("Любой"), color=KeyboardButtonColor.SECONDARY)
        kb.add(Text("Меню"), color=KeyboardButtonColor.NEGATIVE)
        return kb.get_json()

    if state == SearchStates.RECENT_DAYS:
        kb = Keyboard(inline=True)
        kb.add(Text("7 дней"), color=KeyboardButtonColor.PRIMARY)
        kb.add(Text("30 дней"), color=KeyboardButtonColor.PRIMARY)
        kb.row()
        kb.add(Text("Не важно"), color=KeyboardButtonColor.SECONDARY)
        kb.row()
        kb.add(Text("Назад"), color=KeyboardButtonColor.NEGATIVE)
        kb.add(Text("Выход"), color=KeyboardButtonColor.NEGATIVE)
        return kb.get_json()

    kb = Keyboard(inline=True)
    kb.add(Text("Пропустить"), color=KeyboardButtonColor.SECONDARY)
    kb.row()
    kb.add(Text("Назад"), color=KeyboardButtonColor.NEGATIVE)
    kb.add(Text("Меню"), color=KeyboardButtonColor.NEGATIVE)
    return kb.get_json()


async def prompt_search_state(message: Message, state) -> None:
    prompt = SEARCH_PROMPTS.get(state, "Введите значение:")
    await message.answer(prompt, keyboard=search_kb_for_state_inline(state))


def _vk_api_call(method: str, params: Dict[str, Any], token: Optional[str] = None) -> Dict[str, Any]:
    payload = dict(params)
    access_token = token or TOKEN_FOR_BOT
    if access_token:
        payload.setdefault("access_token", access_token)
    payload.setdefault("v", API_V)
    url = f"https://api.vk.com/method/{method}"
    try:
        response = requests.post(url, data=payload, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        return {"error": {"error_msg": str(exc)}}


FIELD_LABELS = {
    "district": "Район",
    "address": "Адрес",
    "floor": "Этаж",
    "rooms": "Комнат",
    "price": "Цена",
    "fio": "Контакт",
    "phone": "Телефон",
}


def parse_post_text(text: str) -> Dict[str, Any]:
    parsed: Dict[str, Any] = {}
    if not text:
        return parsed

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        for key, label in FIELD_LABELS.items():
            marker = f"{label}:"
            if marker in line:
                value = line.split(marker, 1)[1].strip()
                parsed[key] = value
                if key in {"price", "rooms", "floor"}:
                    digits = re.sub(r"\D", "", value)
                    if digits:
                        parsed[f"{key}_value"] = int(digits)
                break
    return parsed


def search_posts(filters: Dict[str, Any], limit: Optional[int] = None, fetch_count: int = 100) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    if not GROUP_ID:
        return [], "GROUP_ID не настроен"
    if not TOKEN_FOR_BOT:
        return [], "Нет access token для запросов к VK"

    owner_id = -abs(int(GROUP_ID))
    payload = {
        "owner_id": owner_id,
        "count": fetch_count,
        "offset": 0,
    }

    token_for_wall = USER_TOKEN or UPLOAD_TOKEN
    if not token_for_wall:
        return [], "Добавьте USER_TOKEN или UPLOAD_TOKEN с правами wall/groups для поиска по постам"

    resp = _vk_api_call("wall.get", payload, token=token_for_wall)
    if "error" in resp:
        err_msg = resp["error"].get("error_msg", "Неизвестная ошибка VK")
        if err_msg.lower().startswith("group authorization failed"):
            err_msg = "Токен не подходит для wall.get. Убедитесь, что USER_TOKEN или UPLOAD_TOKEN выданы администратору с правами wall,groups."
        return [], err_msg

    items = resp.get("response", {}).get("items", [])
    if not isinstance(items, list):
        return [], "Некорректный ответ от VK"

    target_limit = limit if limit is not None else SEARCH_RESULTS_LIMIT
    if target_limit is not None and target_limit <= 0:
        target_limit = None

    recent_days_filter = filters.get("recent_days")
    if isinstance(recent_days_filter, str):
        try:
            recent_days_filter = int(recent_days_filter.strip())
        except ValueError:
            recent_days_filter = None
    recent_threshold: Optional[float] = None
    if isinstance(recent_days_filter, int) and recent_days_filter > 0:
        recent_threshold = time.time() - recent_days_filter * 86400

    district_filter = filters.get("district")
    price_min = filters.get("price_min")
    price_max = filters.get("price_max")
    rooms_filter = filters.get("rooms")

    matches: List[Dict[str, Any]] = []
    for item in items:
        if recent_threshold is not None:
            item_date = item.get("date")
            if isinstance(item_date, str):
                try:
                    item_date = int(item_date.strip())
                except ValueError:
                    item_date = None
            if not isinstance(item_date, (int, float)):
                continue
            if item_date < recent_threshold:
                continue
        text = item.get("text", "")
        parsed = parse_post_text(text)
        if not parsed:
            continue

        if district_filter:
            district = parsed.get("district")
            if not district or district.lower() != district_filter.lower():
                continue

        price_value = parsed.get("price_value")
        if price_min is not None:
            if price_value is None or price_value < price_min:
                continue
        if price_max is not None:
            if price_value is None or price_value > price_max:
                continue

        rooms_value = parsed.get("rooms_value")
        if rooms_filter is not None:
            if rooms_value is None or rooms_value != rooms_filter:
                continue

        matches.append({"item": item, "parsed": parsed})
        if target_limit is not None and len(matches) >= target_limit:
            break

    return matches, None


def format_search_result(index: int, item: Dict[str, Any]) -> str:
    post_id = item.get("id")
    if post_id is None:
        return f"Объявление №{index}"
    return f"Объявление №{index}"


def get_search_session(uid: str) -> Dict[str, Any]:
    return search_sessions.setdefault(uid, {})


def extract_int(text: str) -> Optional[int]:
    if not text:
        return None
    normalized = text.replace(" ", "")
    digits = re.sub(r"\D", "", normalized)
    if not digits:
        return None
    first_digit_index = next((idx for idx, ch in enumerate(normalized) if ch.isdigit()), None)
    if first_digit_index is None:
        return None
    sign = -1 if "-" in normalized[:first_digit_index + 1] else 1
    return sign * int(digits)


async def run_search_and_reply(message: Message, uid: str) -> None:
    session = search_sessions.get(uid, {})
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
        return

    if not matches:
        await message.answer(
            "По заданным фильтрам ничего не найдено. Попробуйте изменить параметры.",
            keyboard=main_menu_inline(),
        )
        return

    await message.answer(f"Нашёл {len(matches)} подходящих объявлений. Показываю их ниже.")
    for idx, match in enumerate(matches, start=1):
        item = match["item"]
        text = format_search_result(idx, item)
        post_id = item.get("id")
        if post_id is not None:
            owner_part = -abs(int(GROUP_ID))
            attachment = f"wall{owner_part}_{post_id}"
            await message.answer(text, attachment=attachment)
        else:
            await message.answer(text)

    await message.answer(
        "Чтобы запустить новый поиск, вернитесь в меню и выберите снова «Посмотреть объявления».",
        keyboard=main_menu_inline(),
    )


# ---------------------------
# Search flow handlers
# ---------------------------
def _search_reset(uid: str) -> None:
    search_sessions.pop(uid, None)


@bot.on.message(state=SearchStates.DISTRICT)
async def search_district_handler(message: Message):
    uid = str(message.from_id)
    peer = message.peer_id
    text = (message.text or "").strip()

    if text == "Меню":
        _search_reset(uid)
        await bot.state_dispenser.delete(peer)
        await message.answer("Вы вернулись в меню.", keyboard=main_menu_inline())
        return

    valid = {"Автозаводский", "Канавинский", "Ленинский", "Московский", "Нижегородский", "Приокский", "Советский", "Сормовский", "Любой"}
    if text not in valid:
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
    uid = str(message.from_id)
    peer = message.peer_id
    text = (message.text or "").strip()

    if text == "Меню":
        _search_reset(uid)
        await bot.state_dispenser.delete(peer)
        await message.answer("Вы вернулись в меню.", keyboard=main_menu_inline())
        return
    if text == "Назад":
        await bot.state_dispenser.set(peer, SearchStates.DISTRICT)
        await prompt_search_state(message, SearchStates.DISTRICT)
        return

    session = get_search_session(uid)
    session.pop("price_max", None)  # сбрасываем max, если min вводят заново

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
    uid = str(message.from_id)
    peer = message.peer_id
    text = (message.text or "").strip()

    if text == "Меню":
        _search_reset(uid)
        await bot.state_dispenser.delete(peer)
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
    uid = str(message.from_id)
    peer = message.peer_id
    text = (message.text or "").strip()

    if text == "Меню":
        _search_reset(uid)
        await bot.state_dispenser.delete(peer)
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

def _is_start_trigger(message: Message) -> bool:
    text_value = (message.text or "").strip().lower()
    if text_value in START_COMMANDS:
        return True
    payload = getattr(message, "payload", None)
    payload_getter = getattr(message, "dict", None)
    if not payload and callable(payload_getter):
        try:
            payload = payload_getter().get("payload")
        except Exception:
            payload = None
    if not payload:
        return False
    if isinstance(payload, str):
        try:
            data = json.loads(payload)
        except (ValueError, TypeError):
            return False
    elif isinstance(payload, dict):
        data = payload
    else:
        return False
    command = data.get("command")
    return isinstance(command, str) and command.lower() == "start"

# ---------------------------
# Entry / Menu
# ---------------------------
@bot.on.message(state=SearchStates.RECENT_DAYS)
async def search_recent_days_handler(message: Message):
    uid = str(message.from_id)
    peer = message.peer_id
    text = (message.text or "").strip()

    if text == "Выход":
        _search_reset(uid)
        await bot.state_dispenser.delete(peer)
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
        await message.answer("Пожалуйста, выберите вариант из меню.", keyboard=search_kb_for_state_inline(SearchStates.RECENT_DAYS))
        return

    await bot.state_dispenser.delete(peer)
    await run_search_and_reply(message, uid)
    _search_reset(uid)


@bot.on.message(func=_is_start_trigger)
async def start_command(message: Message):
    user_id = getattr(message, "from_id", None)
    peer = message.peer_id
    uid_int: Optional[int] = None
    if user_id is not None:
        try:
            uid_int = int(user_id)
            if _allow_greeted_recently(uid_int):
                return
        except (TypeError, ValueError):
            uid_int = None
    if uid_int is not None:
        _mark_allow_greeting(uid_int)

    try:
        await bot.state_dispenser.delete(peer)
    except Exception:
        pass
    if user_id is not None:
        try:
            user_data.pop(str(user_id), None)
        except Exception:
            pass

    await message.answer(f"{MENU_GREETING}", keyboard=main_menu_inline())

@bot.on.raw_event(GroupEventType.MESSAGE_ALLOW, dataclass=GroupTypes.MessageAllow)
async def show_menu_on_allow(event: GroupTypes.MessageAllow):
    user_id = getattr(getattr(event, "object", None), "user_id", None)
    if not user_id:
        return
    uid_int: Optional[int] = None
    try:
        uid_int = int(user_id)
        if _allow_greeted_recently(uid_int):
            return
        _mark_allow_greeting(uid_int)
    except (TypeError, ValueError):
        uid_int = None

    try:
        await bot.api.messages.send(
            user_id=user_id,
            random_id=_random_id(),
            message=f"{MENU_GREETING}",
            keyboard=main_menu_inline(),
        )
    except Exception:
        pass

@bot.on.message(text="Посмотреть")
async def view_rents(message: Message):
    uid = str(message.from_id)
    search_sessions[uid] = {}
    await bot.state_dispenser.set(message.peer_id, SearchStates.DISTRICT)
    await message.answer("Подберём объявления из сообщества по вашим фильтрам.")
    await prompt_search_state(message, SearchStates.DISTRICT)

@bot.on.message(text="Выложить")
async def post_rent_start(message: Message):
    uid = str(message.from_id)
    user_data[uid] = {}
    await bot.state_dispenser.set(message.peer_id, RentStates.DISTRICT)
    await message.answer(STATE_PROMPTS[RentStates.DISTRICT], keyboard=state_keyboard(uid, RentStates.DISTRICT))

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
    if text == "Отмена":
        if await maybe_back_to_preview(message, uid):
            return

    valid = {"Автозаводский", "Канавинский", "Ленинский", "Московский", "Нижегородский", "Приокский", "Советский", "Сормовский"}
    if text not in valid:
        await message.answer("Пожалуйста, выберите район из кнопок.", keyboard=state_keyboard(uid, RentStates.DISTRICT))
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
    if text == "Отмена":
        if await maybe_back_to_preview(message, uid):
            return
        text = "Назад"
    if text == "Назад":
        await bot.state_dispenser.set(peer, RentStates.DISTRICT)
        await message.answer(STATE_PROMPTS[RentStates.DISTRICT], keyboard=state_keyboard(uid, RentStates.DISTRICT))
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
    if text == "Отмена":
        if await maybe_back_to_preview(message, uid):
            return
        text = "Назад"
    if text == "Назад":
        await bot.state_dispenser.set(peer, RentStates.ADDRESS)
        await prompt_for_state(message, RentStates.ADDRESS)
        return

    try:
        user_data[uid]["floor"] = int(text)
    except Exception:
        await message.answer("Этаж должен быть числом. Введите цифрами.", keyboard=state_keyboard(uid, RentStates.FLOOR))
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
    if text == "Отмена":
        if await maybe_back_to_preview(message, uid):
            return
        text = "Назад"
    if text == "Назад":
        await bot.state_dispenser.set(peer, RentStates.FLOOR)
        await prompt_for_state(message, RentStates.FLOOR)
        return

    try:
        user_data[uid]["rooms"] = int(text)
    except Exception:
        await message.answer("Количество комнат должно быть числом. Введите цифрами.", keyboard=state_keyboard(uid, RentStates.ROOMS))
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
        await message.answer("Цена должна быть числом. Попробуйте ещё раз.", keyboard=state_keyboard(uid, RentStates.PRICE))
        return
    if value <= 0:
        await message.answer("Цена должна быть положительной. Попробуйте ещё раз.", keyboard=state_keyboard(uid, RentStates.PRICE))
        return
    user_data[uid]["price"] = int(value)

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
    if text == "Отмена":
        if await maybe_back_to_preview(message, uid):
            return
        text = "Назад"
    if text == "Назад":
        await bot.state_dispenser.set(peer, RentStates.PRICE)
        await prompt_for_state(message, RentStates.PRICE)
        return

    user_data[uid]["description"] = message.text
    # Next step: photos
    await bot.state_dispenser.set(peer, RentStates.PHOTOS)
    await message.answer(STATE_PROMPTS.get(RentStates.PHOTOS, "Прикрепите фото или Пропустить."), keyboard=photos_keyboard(uid))

# ---------------------------
# PHOTOS (accept photo attachments, "Готово"/"Пропустить")
# ---------------------------
@bot.on.message(state=RentStates.PHOTOS)
async def photos_handler(message: Message):
    uid = str(message.from_id)
    peer = message.peer_id
    text = (message.text or "").strip()
    user_data.setdefault(uid, {})
    cancel_label = "Отмена" if user_data[uid].get("back_to_preview") else "Назад"

    # Buttons
    if text == "Меню":
        await bot.state_dispenser.delete(peer)
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

    # If attachments contain photos - extract and store
    photo_urls = await extract_photo_urls_from_message(message)
    if photo_urls:
        stored = user_data[uid].setdefault("photo_urls", [])
        new_urls = [url for url in photo_urls if url not in stored]
        if not new_urls:
            await message.answer(
                "These photos are already attached. Add new ones or use the buttons below.",
                keyboard=photos_keyboard(uid),
            )
            return

        stored.extend(new_urls)
        added = len(new_urls)
        total = len(stored)
        await message.answer(
            f"Added {added} photo(s). Total stored: {total}.",
            keyboard=photos_keyboard(uid),
        )
        return

    # otherwise prompt user
    await message.answer("Пожалуйста, пришлите фото (файл) или нажмите «Пропустить»/«Готово».", keyboard=photos_keyboard(uid))

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
    if text == "Отмена":
        if await maybe_back_to_preview(message, uid):
            return
        text = "Назад"
    if text == "Назад":
        await bot.state_dispenser.set(peer, RentStates.PHOTOS)
        await message.answer(STATE_PROMPTS.get(RentStates.PHOTOS, "Прикрепите фото или Пропустить."), keyboard=photos_keyboard(uid))
        return

    if not text or len(text) < 2:
        await message.answer("Пожалуйста, укажите ФИО (имя и фамилия).", keyboard=state_keyboard(uid, RentStates.FIO))
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
    if text == "Отмена":
        if await maybe_back_to_preview(message, uid):
            return
        text = "Назад"
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
        await message.answer("Неверный номер — должно быть не менее 7 цифр. Попробуйте ещё раз.", keyboard=state_keyboard(uid, RentStates.PHONE))
        return

    user_data[uid]["phone"] = normalized

    # show preview
    draft = user_data[uid]
    price_formatted = format_price_display(draft.get("price"))
    preview_text = (
        "📌 Предпросмотр объявления:\n\n"
        f"💰 Цена: {price_formatted}\n"
        f"🏙 Район: {draft.get('district','—')}\n"
        f"📍 Адрес: {draft.get('address','—')}\n"
        f"🏢 Этаж: {draft.get('floor','—')}\n"
        f"🚪 Комнат: {draft.get('rooms','—')}\n"
        f"📝 Описание:\n{draft.get('description','—')}\n\n"
        f"👤 Контакт: {draft.get('fio','—')}\n"
        f"📞 Телефон: {draft.get('phone','—')}\n\n"
        "Нажмите «Отправить», чтобы поставить объявление в отложенные записи сообщества, "
        "или выберите «Изменить ...», чтобы редактировать поле."
    )
    await bot.state_dispenser.set(peer, RentStates.PREVIEW)
    await message.answer(preview_text, keyboard=kb_preview_inline(draft))

# ---------------------------
# Preview actions: Send and Edit buttons
# ---------------------------
@bot.on.message(text="Отправить")
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
        resp = send_to_scheduled(text=text, attachments=attachments, delay_seconds=DEFAULT_SCHEDULE_DELAY)
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
            f"✅ Готово — объявление отправлено в отложенные.",
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
@bot.on.message(text="Район")
async def edit_district(message: Message):
    uid = str(message.from_id)
    user_data.setdefault(uid, {})["back_to_preview"] = True
    await bot.state_dispenser.set(message.peer_id, RentStates.DISTRICT)
    await message.answer(STATE_PROMPTS[RentStates.DISTRICT], keyboard=state_keyboard(uid, RentStates.DISTRICT))

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

@bot.on.message(text="Комнат")
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

# ---------------------------
# Fallback global handlers (optional)
# ---------------------------
@bot.on.message(text=["Назад", "Меню", "Отмена"])
async def global_back_or_menu(message: Message):
    text = (message.text or "").strip()
    peer = message.peer_id
    if text == "Меню":
        await bot.state_dispenser.delete(peer)
        await message.answer("Вы вернулись в меню.", keyboard=main_menu_inline())
        return
    await bot.state_dispenser.delete(peer)
    await message.answer("Вы вернулись в меню.", keyboard=main_menu_inline())

@bot.on.message()
async def fallback_menu(message: Message):
    if getattr(message, "state_peer", None):
        return
    if _is_start_trigger(message):
        return
    text_value = (message.text or "").strip().lower()
    if text_value in START_COMMANDS or text_value in {"меню", "назад", "отмена"}:
        return
    await message.answer(f"{MENU_GREETING}", keyboard=main_menu_inline())

