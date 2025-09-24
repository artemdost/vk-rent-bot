from vkbottle.bot import Bot, Message
from dotenv import load_dotenv
import os
load_dotenv()

token = os.getenv("VK_TOKEN")

bot = Bot(token=token)

@bot.on.message(text="Привет")
async def hi_handler(message: Message):
    await message.answer("Привет")

bot.run_forever()