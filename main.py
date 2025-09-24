from vkbottle.bot import Bot, Message
from dotenv import load_dotenv
import os
load_dotenv()

token = os.getenv("VK_TOKEN")

bot = Bot(token)

@bot.on.message(text="Привет")
async def hi_handler(message: Message):
    users_info = await bot.api.users.get(message.from_id)
    await message.answer("Привет, {}".format(users_info[0].first_name))

bot.run_forever()