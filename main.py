from vkbottle.bot import Bot, Message
from dotenv import load_dotenv
import os
from vkbottle import Bot, Keyboard, KeyboardButtonColor, Text
from vkbottle import BaseStateGroup
'''from vkbottle.dispatch.rules.base import StateRule
from vkbottle.dispatch.views import StatefulView
from vkbottle.dispatch.views import StateFilter
from vkbottle.modules import json'''
load_dotenv()

token = os.getenv("VK_TOKEN")

bot = Bot(token=token)

# --- Состояния --- #
class RentStates(BaseStateGroup):
    DISTRICT = "district"
    ADDRESS = "address"
    FLOOR = "floor"
    ROOMS = "rooms"
    PRICE = "price"
    DESCRIPTION = "description"

# --- Клавиатура с выьором начального действия --- #
def main_menu_keyboard():
    kb = (
        Keyboard(one_time=False)
        .add(Text("Выложить объявление"), color=KeyboardButtonColor.PRIMARY)
        .add(Text("Посмотреть объявления"), color=KeyboardButtonColor.SECONDARY)
    )
    return kb.get_json()

# --- Клавиатура с районами ---
def district_keyboard():
    kb = (
        Keyboard(one_time=True, inline=False)
        .add(Text("Центр"), color=KeyboardButtonColor.PRIMARY)
        .add(Text("Север"), color=KeyboardButtonColor.PRIMARY)
        .row()
        .add(Text("Юг"), color=KeyboardButtonColor.PRIMARY)
        .add(Text("Восток"), color=KeyboardButtonColor.PRIMARY)
        .row()
        .add(Text("Запад"), color=KeyboardButtonColor.PRIMARY)
    )
    return kb.get_json()


# --- Хранилище данных пользователя ---
user_data = {}


# --- Старт ---
@bot.on.message(text="/start")
async def start(message: Message):
    await message.answer("Привет! Выберите действие:", keyboard=main_menu_keyboard())


# --- Главное меню ---
@bot.on.message(text="Выложить объявление")
async def post_rent(message: Message):
    user_data[message.from_id] = {}
    await bot.state_dispenser.set(message.peer_id, RentStates.DISTRICT)
    await message.answer("Выберите район:", keyboard=district_keyboard())


@bot.on.message(text="Посмотреть объявления")
async def view_rent(message: Message):
    # Здесь нужно добавить логику показа объявлений
    await message.answer("Здесь будут объявления (пока заглушка).")


# --- Выбор района ---
@bot.on.message(state=RentStates.DISTRICT)
async def district_handler(message: Message):
    if message.text not in ["Центр", "Север", "Юг", "Восток", "Запад"]:
        await message.answer("Пожалуйста, выберите район из кнопок.")
        return

    user_data[message.from_id]["district"] = message.text
    await bot.state_dispenser.set(message.peer_id, RentStates.ADDRESS)
    await message.answer("Введите адрес:")


# --- Адрес ---
@bot.on.message(state=RentStates.ADDRESS)
async def address_handler(message: Message):
    user_data[message.from_id]["address"] = message.text
    await bot.state_dispenser.set(message.peer_id, RentStates.FLOOR)
    await message.answer("Введите этаж:")


# --- Этаж ---
@bot.on.message(state=RentStates.FLOOR)
async def floor_handler(message: Message):
    user_data[message.from_id]["floor"] = message.text
    await bot.state_dispenser.set(message.peer_id, RentStates.ROOMS)
    await message.answer("Введите количество комнат:")


# --- Количество комнат ---
@bot.on.message(state=RentStates.ROOMS)
async def rooms_handler(message: Message):
    user_data[message.from_id]["rooms"] = message.text
    await bot.state_dispenser.set(message.peer_id, RentStates.PRICE)
    await message.answer("Введите цену:")


# --- Цена ---
@bot.on.message(state=RentStates.PRICE)
async def price_handler(message: Message):
    user_data[message.from_id]["price"] = message.text
    await bot.state_dispenser.set(message.peer_id, RentStates.DESCRIPTION)
    await message.answer("Введите описание квартиры:")


# --- Описание ---
@bot.on.message(state=RentStates.DESCRIPTION)
async def description_handler(message: Message):
    user_data[message.from_id]["description"] = message.text

    data = user_data[message.from_id]
    text = (
        f"📌 Новое объявление:\n\n"
        f"🏙 Район: {data['district']}\n"
        f"📍 Адрес: {data['address']}\n"
        f"🏢 Этаж: {data['floor']}\n"
        f"🚪 Комнат: {data['rooms']}\n"
        f"💰 Цена: {data['price']}\n"
        f"📝 Описание: {data['description']}"
    )

    await message.answer(text)
    await bot.state_dispenser.delete(message.peer_id)


bot.run_forever()