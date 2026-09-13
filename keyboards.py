# keyboards.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import ICON_IDS


def main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Играть", callback_data="open_games", style="success", icon_custom_emoji_id=ICON_IDS["fire"]),
            InlineKeyboardButton(text="Игровые чаты", callback_data="open_chats", style="primary")
        ],
        [
            InlineKeyboardButton(text="Профиль", callback_data="profile", style="primary", icon_custom_emoji_id=ICON_IDS["rocket"]),
            InlineKeyboardButton(text="Реф Программа", callback_data="referrals", style="primary", icon_custom_emoji_id=ICON_IDS["cash"])
        ],
        [
            InlineKeyboardButton(text="Кешбэк", callback_data="open_cashback", style="success", icon_custom_emoji_id=ICON_IDS["cash"]),
            InlineKeyboardButton(text="Топ игроков", callback_data="open_top", style="primary", icon_custom_emoji_id=ICON_IDS["trophy"])
        ],
        [InlineKeyboardButton(text="Правила", callback_data="rules", icon_custom_emoji_id=ICON_IDS["shield"])]
    ])


def games_select_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Кости", callback_data="game_dice", style="primary"),
            InlineKeyboardButton(text="Мины", callback_data="game_mines", style="danger", icon_custom_emoji_id=ICON_IDS["mine"]),
            InlineKeyboardButton(text="Башня", callback_data="game_tower", style="success", icon_custom_emoji_id=ICON_IDS["star"])
        ],
        [InlineKeyboardButton(text="⚽ Ставки на спорт", callback_data="game_sport", style="primary", icon_custom_emoji_id=ICON_IDS["fire"])],
        [InlineKeyboardButton(text="Назад", callback_data="back_to_main", style="danger", icon_custom_emoji_id=ICON_IDS["cross"])]
    ])


def back_to_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_to_main", style="primary")]
    ])