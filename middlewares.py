# middlewares.py
import time
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from database import get_user


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, slowmode_seconds: float = 1):
        self.slowmode = slowmode_seconds
        self.users_last_action: Dict[int, float] = {}

    async def __call__(self, handler, event, data):
        user_id = None
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery) and event.from_user:
            user_id = event.from_user.id
        if user_id:
            u = await get_user(user_id)
            if u and u["is_banned"]:
                if isinstance(event, CallbackQuery):
                    await event.answer("⛔ Вы заблокированы в системе.", show_alert=True)
                return
            now = time.time()
            last_action = self.users_last_action.get(user_id, 0.0)
            elapsed = now - last_action
            is_game_click = False
            if isinstance(event, CallbackQuery) and event.data:
                if event.data.startswith("m_clk_") or event.data.startswith("t_clk_"):
                    is_game_click = True
            if not is_game_click and elapsed < self.slowmode:
                time_left = round(self.slowmode - elapsed, 1)
                warning = f"⏳ Задержка! Подождите {time_left} сек."
                if isinstance(event, CallbackQuery):
                    await event.answer(warning, show_alert=True)
                elif isinstance(event, Message):
                    await event.reply(f"<blockquote>{warning}</blockquote>", parse_mode="HTML")
                return
            self.users_last_action[user_id] = time.time()
        return await handler(event, data)