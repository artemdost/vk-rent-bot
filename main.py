# main.py
import asyncio
import core      # регистрирует bot, состояния и функции
import post_flow  # регистрирует хэндлеры, использует core.bot
from db import init_db

async def main():
    await init_db()
    await core.bot.run_forever()

if __name__ == "__main__":
    asyncio.run(main())
