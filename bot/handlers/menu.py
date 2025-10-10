"""
Обработчики главного меню и базовых команд.
"""
import json
import time
import random
from typing import Optional, Dict
from vkbottle.bot import Message
from vkbottle import GroupEventType, GroupTypes

from bot.bot_instance import bot, user_data
from bot.config import MENU_GREETING, START_COMMANDS, SUPPORT_URL, ALLOW_GREETING_SUPPRESS_SECONDS
from bot.keyboards import main_menu_inline

# Временное хранилище для подавления повторных приветствий
_recent_allow_greetings: Dict[int, float] = {}


def _cleanup_recent_allow(now: float) -> None:
    """Очищает устаревшие записи о приветствиях."""
    stale = [
        uid
        for uid, mark in _recent_allow_greetings.items()
        if now - mark > ALLOW_GREETING_SUPPRESS_SECONDS
    ]
    for uid in stale:
        _recent_allow_greetings.pop(uid, None)


def _mark_allow_greeting(user_id: int) -> None:
    """Отмечает, что пользователю было отправлено приветствие."""
    now = time.monotonic()
    _recent_allow_greetings[user_id] = now
    _cleanup_recent_allow(now)


def _allow_greeted_recently(user_id: int) -> bool:
    """Проверяет, было ли недавно отправлено приветствие пользователю."""
    now = time.monotonic()
    ts = _recent_allow_greetings.pop(user_id, None)
    _cleanup_recent_allow(now)
    return ts is not None and now - ts <= ALLOW_GREETING_SUPPRESS_SECONDS


def _random_id() -> int:
    """Генерирует случайный ID для сообщения."""
    return random.randint(-2_147_483_648, 2_147_483_647)


def _is_start_trigger(message: Message) -> bool:
    """Проверяет, является ли сообщение командой старт."""
    text_value = (message.text or "").strip().lower()
    if text_value in START_COMMANDS:
        return True

    payload = getattr(message, "payload", None)
    payload_getter = getattr(message, "dict", None)

    if not payload and callable(payload_getter):
        try:
            payload = payload_getter().get("payload")
        except Exception:
            payload = None

    if not payload:
        return False

    if isinstance(payload, str):
        try:
            data = json.loads(payload)
        except (ValueError, TypeError):
            return False
    elif isinstance(payload, dict):
        data = payload
    else:
        return False

    command = data.get("command")
    return isinstance(command, str) and command.lower() == "start"


@bot.on.message(func=_is_start_trigger)
async def start_command(message: Message):
    """Обработчик команды /start."""
    user_id = getattr(message, "from_id", None)
    peer = message.peer_id
    uid_int: Optional[int] = None

    if user_id is not None:
        try:
            uid_int = int(user_id)
            if _allow_greeted_recently(uid_int):
                return
        except (TypeError, ValueError):
            uid_int = None

    if uid_int is not None:
        _mark_allow_greeting(uid_int)

    try:
        try:
            await bot.state_dispenser.delete(peer)
        except (KeyError, Exception):
            pass
    except Exception:
        pass

    if user_id is not None:
        try:
            user_data.pop(str(user_id), None)
        except Exception:
            pass

    await message.answer(f"{MENU_GREETING}", keyboard=main_menu_inline())


@bot.on.raw_event(GroupEventType.MESSAGE_ALLOW, dataclass=GroupTypes.MessageAllow)
async def show_menu_on_allow(event: GroupTypes.MessageAllow):
    """Показывает меню при разрешении сообщений от сообщества."""
    user_id = getattr(getattr(event, "object", None), "user_id", None)
    if not user_id:
        return

    uid_int: Optional[int] = None
    try:
        uid_int = int(user_id)
        if _allow_greeted_recently(uid_int):
            return
        _mark_allow_greeting(uid_int)
    except (TypeError, ValueError):
        uid_int = None

    try:
        await bot.api.messages.send(
            user_id=user_id,
            random_id=_random_id(),
            message=f"{MENU_GREETING}",
            keyboard=main_menu_inline(),
        )
    except Exception:
        pass


@bot.on.message(text="Поддержка")
async def support_handler(message: Message):
    """Обработчик кнопки 'Поддержка'."""
    support_text = (
        "📞 Поддержка\n\n"
        "Если у вас возникли вопросы или нужна помощь,\n"
        "обратитесь к администратору:\n\n"
        f"👤 {SUPPORT_URL}"
    )
    await message.answer(support_text, keyboard=main_menu_inline())


@bot.on.message(text=["Назад", "Меню", "Отмена"])
async def global_back_or_menu(message: Message):
    """Глобальный обработчик для возврата в меню."""
    peer = message.peer_id

    try:
        try:
            await bot.state_dispenser.delete(peer)
        except (KeyError, Exception):
            pass
    except (KeyError, Exception):
        pass

    await message.answer("Вы вернулись в меню.", keyboard=main_menu_inline())


@bot.on.message()
async def fallback_menu(message: Message):
    """Fallback обработчик - показывает меню при непонятных командах."""
    if getattr(message, "state_peer", None):
        return
    if _is_start_trigger(message):
        return

    text_value = (message.text or "").strip().lower()
    if text_value in START_COMMANDS or text_value in {"меню", "назад", "отмена"}:
        return

    await message.answer(f"{MENU_GREETING}", keyboard=main_menu_inline())
