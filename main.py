# main.py
import core      # регистрирует bot, состояния и функции
import post_flow  # регистрирует хэндлеры, использует core.bot

if __name__ == "__main__":
    core.bot.run_forever()
