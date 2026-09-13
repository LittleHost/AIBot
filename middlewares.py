# middlewares.py
import time
from typing import Dict
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from database import get_user, set_chat_link
from config import LOG_CHAT_ID
from utils import log_event


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


class ChatLinkMiddleware(BaseMiddleware):
    """Автосохранение ссылки чата БЕЗ блокировки остальных хендлеров."""

    async def __call__(self, handler, event, data):
        if isinstance(event, Message) and event.chat.type in ("group", "supergroup"):
            if event.chat.username:
                try:
                    await set_chat_link(event.chat.id, f"https://t.me/{event.chat.username}")
                except Exception:
                    pass
        return await handler(event, data)


class GlobalLogMiddleware(BaseMiddleware):
    """Логирует ВСЕ сообщения и нажатия кнопок в лог-чат.
    Ставится как outer_middleware на dp.update."""

    # Не логируем эти callback_data — они шумные/технические
    SKIP_CALLBACK_PREFIXES = (
        "none",
        "m_clk_",   # клики в минах — логируются через log_event внутри
        "t_clk_",   # клики в башне
    )

    async def __call__(self, handler, event, data):
        try:
            # Message
            if isinstance(event, Message):
                u = event.from_user
                if u and not u.is_bot:
                    text = event.text or ""
                    chat_info = ""
                    if event.chat.type in ("group", "supergroup"):
                        chat_info = f"\n📍 Чат: <b>{event.chat.title or event.chat.id}</b> (<code>{event.chat.id}</code>)"
                    # Пропускаем технические апдейты
                    if text or event.dice or event.photo or event.document:
                        preview = (text[:200] + "...") if len(text) > 200 else text
                        await log_event(
                            event.bot,
                            "💬 Сообщение",
                            u,
                            f"Текст: <code>{preview}</code>{chat_info}"
                        )
            # CallbackQuery
            elif isinstance(event, CallbackQuery):
                cb = event.data or ""
                if not any(cb.startswith(p) for p in self.SKIP_CALLBACK_PREFIXES):
                    msg_text = ""
                    try:
                        if event.message and event.message.caption:
                            msg_text = f"\n📎 На сообщении: <i>{event.message.caption[:100]}</i>"
                    except Exception:
                        pass
                    await log_event(
                        event.bot,
                        f"🖱 Callback: <code>{cb}</code>",
                        event.from_user,
                        f"Кнопка нажата{msg_text}"
                    )
        except Exception as e:
            # Логгер не должен ломать основной поток
            import logging
            logging.error(f"GlobalLogMiddleware error: {e}")

        return await handler(event, data)
