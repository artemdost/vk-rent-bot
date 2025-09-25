# core.py
import os
from dotenv import load_dotenv
from vkbottle.bot import Bot, Message
from vkbottle import Keyboard, KeyboardButtonColor, Text
from vkbottle import BaseStateGroup

load_dotenv()

VK_TOKEN = os.getenv("VK_TOKEN")  # токен бота (или community token, если используешь)
if not VK_TOKEN:
    raise RuntimeError("VK_TOKEN не задан в .env")

bot = Bot(token=VK_TOKEN)

# --- Состояния ---
class RentStates(BaseStateGroup):
    DISTRICT = "district"
    ADDRESS = "address"
    FLOOR = "floor"
    ROOMS = "rooms"
    PRICE = "price"
    DESCRIPTION = "description"
    PREVIEW = "preview"

# --- in-memory хранилище черновиков ---
# ключ: str(user_id) -> dict(черновик)
user_data: dict = {}

# --- тексты подсказок ---
STATE_PROMPTS = {
    RentStates.DISTRICT: "Выберите район:",
    RentStates.ADDRESS: "Введите адрес:",
    RentStates.FLOOR: "Введите этаж (цифрами):",
    RentStates.ROOMS: "Введите количество комнат (цифрами):",
    RentStates.PRICE: "Введите цену (цифрами):",
    RentStates.DESCRIPTION: "Введите описание квартиры:",
}

# --- клавиатуры (INLINE) ---
def main_menu_inline():
    kb = Keyboard(inline=True)
    kb.add(Text("Выложить объявление"))
    kb.add(Text("Посмотреть объявления"))
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
    kb.add(Text("Меню"), color=KeyboardButtonColor.NEGATIVE)  # кнопка меню
    return kb.get_json()

def kb_for_state_inline(state):
    """
    Inline keyboard for step. District has its own keyboard (without Назад).
    Others have Назад + Меню buttons.
    """
    if state == RentStates.DISTRICT:
        return district_keyboard_inline()

    kb = Keyboard(inline=True)
    # add empty row if you want other buttons per state
    kb.add(Text("Назад"), color=KeyboardButtonColor.NEGATIVE)
    kb.add(Text("Меню"), color=KeyboardButtonColor.NEGATIVE)
    return kb.get_json()

def kb_preview_inline(draft: dict):
    kb = Keyboard(inline=True)
    kb.add(Text("Отправить в отложенные"), color=KeyboardButtonColor.POSITIVE)
    kb.add(Text("Изменить район"))
    kb.row()
    kb.add(Text("Изменить адрес"))
    kb.add(Text("Изменить этаж"))
    kb.row()
    kb.add(Text("Изменить комнат"))
    kb.add(Text("Изменить цену"))
    kb.row()
    kb.add(Text("Изменить описание"))
    kb.add(Text("Меню"), color=KeyboardButtonColor.NEGATIVE)
    return kb.get_json()

# helper: отправить подсказку для состояния
async def prompt_for_state(message: Message, state):
    uid = str(message.from_id)
    user_data.setdefault(uid, {})
    prompt = STATE_PROMPTS.get(state, "Действие:")
    # покажем текущее значение, если есть
    val = None
    if state == RentStates.ADDRESS: val = user_data[uid].get("address")
    if state == RentStates.FLOOR: val = user_data[uid].get("floor")
    if state == RentStates.ROOMS: val = user_data[uid].get("rooms")
    if state == RentStates.PRICE: val = user_data[uid].get("price")
    if state == RentStates.DESCRIPTION: val = user_data[uid].get("description")
    extra = f"\n(текущее: {val})" if val is not None else ""
    await message.answer(prompt + extra, keyboard=kb_for_state_inline(state))
