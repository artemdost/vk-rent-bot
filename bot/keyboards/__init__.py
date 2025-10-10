"""Клавиатуры бота."""
from .menu import main_menu_inline, subscription_keyboard
from .rent import (
    district_keyboard_inline,
    kb_for_state_inline,
    kb_preview_inline,
    kb_photos_inline,
)
from .search import search_kb_for_state_inline, search_results_keyboard

__all__ = [
    "main_menu_inline",
    "subscription_keyboard",
    "district_keyboard_inline",
    "kb_for_state_inline",
    "kb_preview_inline",
    "kb_photos_inline",
    "search_kb_for_state_inline",
    "search_results_keyboard",
]
