from vkbottle.bot import Bot, Message
from dotenv import load_dotenv
from vkbottle import Keyboard, KeyboardButtonColor, Text
import os
load_dotenv()

token = os.getenv("VK_TOKEN")

bot = Bot(token=token)

@bot.on.message(text="Привет")
async def hi_handler(message: Message):
    await message.answer("Привет")

@bot.on.message(text="Выложить")
async def choose_district(m: Message):
    kb = (
        Keyboard(one_time=False)  # обычная, не inline
        .add(Text("Сормово"), color=KeyboardButtonColor.PRIMARY)
        .add(Text("Автозавод"), color=KeyboardButtonColor.PRIMARY)
        .row()
        .add(Text("Нагорный"), color=KeyboardButtonColor.PRIMARY)
        .add(Text("Советский"), color=KeyboardButtonColor.PRIMARY)
        .add(Text("Сормово"), color=KeyboardButtonColor.PRIMARY)
        .add(Text("Автозавод"), color=KeyboardButtonColor.PRIMARY)
        .row()
        .add(Text("Нагорный"), color=KeyboardButtonColor.PRIMARY)
        .add(Text("Советский"), color=KeyboardButtonColor.PRIMARY)
    )
    await m.answer("Выбери район Нижнего Новгорода:", keyboard=kb.get_json())

bot.run_forever()