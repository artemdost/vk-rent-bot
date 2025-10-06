# main.py
import core      # регистрирует bot, состояния и функции
import post_flow  # регистрирует хэндлеры, использует core.bot

if __name__ == "__main__":
    try:
        core.bot.run_forever()
    except KeyboardInterrupt:
        print("Bot stopped by user")
    except Exception as e:
        print(f"Bot crashed: {e}")
        raise
