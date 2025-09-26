# core.py
import os
import logging
from dotenv import load_dotenv
from vkbottle.bot import Message
from vkbottle.bot import Bot
from vkbottle import Keyboard, KeyboardButtonColor, Text
from vkbottle import BaseStateGroup
import requests
from typing import Optional, Dict, Any

load_dotenv()

# --- logging ---
LOG = logging.getLogger("core")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# --- env / tokens ---
# Preferred name: USER_TOKEN (если есть user access token администратора).
# Для совместимости также читаем VK_TOKEN.
USER_TOKEN = os.getenv("USER_TOKEN") or os.getenv("VK_TOKEN")
GROUP_TOKEN = os.getenv("GROUP_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID") or 0)
API_V = os.getenv("VK_API_VERSION", "5.199")

if not (USER_TOKEN or GROUP_TOKEN):
    raise RuntimeError("Нужен USER_TOKEN (или VK_TOKEN) или GROUP_TOKEN в .env")

# выбираем токен для bot: предпочитаем user-token (для polling), иначе group-token
TOKEN_FOR_BOT = USER_TOKEN or GROUP_TOKEN
LOG.info("Starting bot: using %s", "USER_TOKEN" if USER_TOKEN else "GROUP_TOKEN")

# --- create bot ---
bot = Bot(token=TOKEN_FOR_BOT)

# --- workaround: если polling вызывает groups.getById без group_ids, подставляем GROUP_ID ---
# Это решает ошибку "group_ids is undefined" при использовании vkbottle polling.
if GROUP_ID:
    try:
        _orig_request = bot.api.request  # type: ignore

        async def _patched_request(method: str, data: Optional[Dict[str, Any]] = None):
            params = dict(data) if data else {}
            if method == "groups.getById":
                # подставим group_ids, если caller забыл
                if not params.get("group_ids") and not params.get("group_id"):
                    params["group_ids"] = str(GROUP_ID)
            return await _orig_request(method, params)

        bot.api.request = _patched_request  # type: ignore
        LOG.info("Applied groups.getById patch with GROUP_ID=%s", GROUP_ID)
    except Exception as e:
        LOG.warning("Failed to apply groups.getById patch: %s", e)

# --- quick token / groups check (non-fatal) ---
def _check_token():
    try:
        r = requests.post(
            "https://api.vk.com/method/groups.getById",
            data={"access_token": TOKEN_FOR_BOT, "v": API_V},
            timeout=5,
        )
        LOG.info("Token check (groups.getById): %s", r.text)
    except Exception as e:
        LOG.warning("Token check failed: %s", e)

_check_token()

# --- Состояния ---
class RentStates(BaseStateGroup):
    DISTRICT = "district"
    ADDRESS = "address"
    FLOOR = "floor"
    ROOMS = "rooms"
    PRICE = "price"
    DESCRIPTION = "description"
    FIO = "fio"
    PHONE = "phone"
    PHOTOS = "photos"
    PREVIEW = "preview"


class SearchStates(BaseStateGroup):
    DISTRICT = "search_district"
    PRICE_MIN = "search_price_min"
    PRICE_MAX = "search_price_max"
    ROOMS = "search_rooms"

# --- in-memory хранилище черновиков ---
user_data: dict = {}

# --- подсказки для состояний ---
STATE_PROMPTS = {
    RentStates.DISTRICT: "Выберите район:",
    RentStates.ADDRESS: "Введите адрес:",
    RentStates.FLOOR: "Введите этаж (цифрами):",
    RentStates.ROOMS: "Введите количество комнат (цифрами):",
    RentStates.PHOTOS: "Прикрепите фото (до 6 штук).",
    RentStates.PRICE: "Введите цену (цифрами):",
    RentStates.DESCRIPTION: "Введите описание квартиры:",
    RentStates.FIO: "Введите ФИО (как вы хотите, чтобы с вами связались):",
    RentStates.PHONE: "Введите номер телефона (пример: +7 912 345-67-89 или 89123456789):",
}

# --- inline клавиатуры ---
def main_menu_inline() -> str:
    kb = Keyboard(inline=True)
    kb.add(Text("Выложить объявление"))
    kb.add(Text("Посмотреть объявления"))
    return kb.get_json()

def district_keyboard_inline(editing: bool = False) -> str:
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
    kb.add(Text("Меню"), color=KeyboardButtonColor.NEGATIVE)
    if editing:
        kb.add(Text("Отмена"), color=KeyboardButtonColor.NEGATIVE)
    return kb.get_json()


def kb_for_state_inline(state, editing: bool = False) -> str:
    if state == RentStates.DISTRICT:
        return district_keyboard_inline(editing=editing)
    kb = Keyboard(inline=True)
    button_title = "Отмена" if editing else "Назад"
    kb.add(Text(button_title), color=KeyboardButtonColor.NEGATIVE)
    kb.add(Text("Меню"), color=KeyboardButtonColor.NEGATIVE)
    return kb.get_json()


def kb_preview_inline(draft: dict) -> str:
    kb = Keyboard(inline=True)
    kb.add(Text("Район"))
    kb.add(Text("Телефон"))
    kb.row()
    kb.add(Text("Адрес"))
    kb.add(Text("Этаж"))
    kb.row()
    kb.add(Text("Комнаты"))
    kb.add(Text("Цена"))
    kb.row()
    kb.add(Text("Описание"))
    kb.add(Text("ФИО"))
    kb.row()
    kb.add(Text("Отправить"), color=KeyboardButtonColor.POSITIVE)
    kb.add(Text("Меню"), color=KeyboardButtonColor.NEGATIVE)
    return kb.get_json()

def kb_photos_inline(editing: bool = False) -> str:
    kb = Keyboard(inline=True)
    kb.add(Text("Готово"))
    kb.add(Text("Пропустить"), color=KeyboardButtonColor.SECONDARY)
    kb.row()
    cancel_title = "Отмена" if editing else "Назад"
    kb.add(Text(cancel_title), color=KeyboardButtonColor.NEGATIVE)
    kb.add(Text("Меню"), color=KeyboardButtonColor.NEGATIVE)
    return kb.get_json()


# helper: prompt_for_state
async def prompt_for_state(message: Message, state):
    uid = str(message.from_id)
    user_data.setdefault(uid, {})
    prompt = STATE_PROMPTS.get(state, "Действие:")

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
    await message.answer(prompt + extra, keyboard=kb_for_state_inline(state, editing=editing))

