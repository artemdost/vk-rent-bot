# core.py
from vkbottle.bot import Bot, Message
from dotenv import load_dotenv
import os
from vkbottle import Keyboard, KeyboardButtonColor, Text
from vkbottle import BaseStateGroup

load_dotenv()
token = os.getenv("VK_TOKEN")
if not token:
    raise RuntimeError("VK_TOKEN не задан")

bot = Bot(token=token)

# ---- состояния ----
class RentStates(BaseStateGroup):
    DISTRICT = "district"
    ADDRESS = "address"
    FLOOR = "floor"
    ROOMS = "rooms"
    PRICE = "price"
    DESCRIPTION = "description"
    PREVIEW = "preview"   # новый стейт — экран предпросмотра

# ---- клавиатуры ----
def main_menu_inline():
    kb = Keyboard(inline=True)
    kb.add(Text("Сдать"), color=KeyboardButtonColor.PRIMARY)
    kb.add(Text("Снять"), color=KeyboardButtonColor.PRIMARY)
    return kb.get_json()

def district_keyboard_inline():
    kb = Keyboard(inline=True)
    kb.add(Text("Центр"), color=KeyboardButtonColor.PRIMARY)
    kb.add(Text("Север"), color=KeyboardButtonColor.PRIMARY)
    kb.row()
    kb.add(Text("Юг"), color=KeyboardButtonColor.PRIMARY)
    kb.add(Text("Восток"), color=KeyboardButtonColor.PRIMARY)
    kb.row()
    kb.add(Text("Запад"), color=KeyboardButtonColor.PRIMARY)
    kb.add(Text("Меню"), color=KeyboardButtonColor.NEGATIVE)
    return kb.get_json()

def kb_with_back_inline():
    kb = Keyboard(inline=True)
    kb.add(Text("Назад"), color=KeyboardButtonColor.NEGATIVE)
    kb.add(Text("Меню"), color=KeyboardButtonColor.NEGATIVE)
    return kb.get_json()

def kb_preview_inline():
    """
    Клавиатура предпросмотра: Разместить и кнопки для редактирования параметров.
    Порядок кнопок — настраиваемый.
    """
    kb = Keyboard(inline=True)
    kb.add(Text("Разместить"), color=KeyboardButtonColor.POSITIVE)
    kb.row()
    # редактирование полей
    kb.add(Text("Изменить район"), color=KeyboardButtonColor.PRIMARY)
    kb.add(Text("Изменить адрес"), color=KeyboardButtonColor.PRIMARY)
    kb.row()
    kb.add(Text("Изменить этаж"), color=KeyboardButtonColor.PRIMARY)
    kb.add(Text("Изменить комнат"), color=KeyboardButtonColor.PRIMARY)
    kb.row()
    kb.add(Text("Изменить цену"), color=KeyboardButtonColor.PRIMARY)
    kb.add(Text("Изменить описание"), color=KeyboardButtonColor.PRIMARY)
    kb.row()
    kb.add(Text("Меню"), color=KeyboardButtonColor.NEGATIVE)
    return kb.get_json()

def kb_for_state_inline(state):
    if normalize_state_name(state) == "district":
        return district_keyboard_inline()
    return kb_with_back_inline()

# ---- подсказки ----
STATE_PROMPTS = {
    "district": "Выберите район:",
    "address": "Введите адрес:",
    "floor": "Введите этаж (цифрами):",
    "rooms": "Введите количество комнат (цифрами):",
    "price": "Введите цену (цифрами):",
    "description": "Введите описание квартиры:",
}

# ---- хранилище ----
user_data = {}          # временные черновики: key = str(user_id) -> dict
published_ads = []      # список "опубликованных" объявлений (пример)

# ---- карта Назад ----
PREV = {
    "address": "district",
    "floor": "address",
    "rooms": "floor",
    "price": "rooms",
    "description": "price",
}

# ---- утилиты ----
def normalize_state_name(any_state) -> str:
    s = str(any_state).lower()
    for name in ("district", "address", "floor", "rooms", "price", "description", "preview"):
        if name in s:
            return name
    return s

async def prompt_for_state(message: Message, state, inline=True):
    uid = str(message.from_id)
    user_data.setdefault(uid, {})
    sname = normalize_state_name(state)
    prompt = STATE_PROMPTS.get(sname, "Действие:")
    current = ""
    if sname in ("district", "address", "floor", "rooms", "price", "description"):
        val = user_data[uid].get(sname)
        if val is not None:
            current = f"\n(текущее: {val})"
    kb = kb_for_state_inline(state) if inline else None
    await message.answer(prompt + current, keyboard=kb)

# ---- глобальные handlers: Назад / Меню (не трогать) ----
@bot.on.message(text="Назад")
async def core_back_handler(message: Message):
    peer = message.peer_id
    current = await bot.state_dispenser.get(peer)
    if not current:
        await bot.state_dispenser.delete(peer)
        await message.answer("Вы вернулись в меню.", keyboard=main_menu_inline())
        return

    cur_name = normalize_state_name(current)
    prev_name = PREV.get(cur_name)
    if prev_name:
        prev_state = getattr(RentStates, prev_name.upper())
        await bot.state_dispenser.set(peer, prev_state)
        await prompt_for_state(message, prev_state, inline=True)
    else:
        await bot.state_dispenser.delete(peer)
        await message.answer("Вы вернулись в меню.", keyboard=main_menu_inline())

@bot.on.message(text="Меню")
async def core_menu_handler(message: Message):
    peer = message.peer_id
    await bot.state_dispenser.delete(peer)
    await message.answer("Вы вернулись в меню.", keyboard=main_menu_inline())
