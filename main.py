# main.py
from core import bot, main_menu_inline
import post_flow  # импорт регистрационных хендлеров и функции start_posting
from vkbottle.bot import Message

# Показываем главное меню и делегируем на post_flow.start_posting для "Сдать".
@bot.on.message(text="/start")
async def start_cmd(message: Message):
    await message.answer("Привет! Выберите действие:", keyboard=main_menu_inline())

# Обработчик для "Сдать" и "Снять" — оставляем в main (минимум логики)
@bot.on.message(text=["Сдать", "сдать"])
async def handle_sdat(message: Message):
    # вызываем функцию из post_flow, которая стартует поток публикации
    await post_flow.start_posting(message)

@bot.on.message(text=["Снять", "снять"])
async def handle_snyt(message: Message):
    # пока заглушка, можно позже подключить поиск
    await message.answer("Функция поиска (снять) пока не реализована — здесь будет список объявлений или фильтр.", keyboard=main_menu_inline())

if __name__ == "__main__":
    bot.run_forever()
