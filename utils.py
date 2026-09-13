# utils.py
import logging
from aiogram.types import CallbackQuery, InlineKeyboardMarkup
from config import LOG_CHAT_ID

logger = logging.getLogger(__name__)


async def log_event(bot, action: str, user=None, extra: str = ""):
    if not LOG_CHAT_ID:
        logger.warning("LOG_CHAT_ID не задан — логи отключены")
        return
    try:
        if user is not None:
            uname = f"@{user.username}" if getattr(user, "username", None) else getattr(user, "first_name", "—")
            uid = getattr(user, "id", "—")
            text = (
                f"📌 <b>Лог</b>\n\n"
                f"<blockquote>"
                f"👤 {uname}\n"
                f"🆔 <code>{uid}</code>\n"
                f"⚙️ Действие: <b>{action}</b>"
            )
            if extra:
                text += f"\n📝 {extra}"
            text += "</blockquote>"
        else:
            text = f"📌 <b>Лог</b>\n\n<blockquote>⚙️ Действие: <b>{action}</b>"
            if extra:
                text += f"\n📝 {extra}"
            text += "</blockquote>"
        await bot.send_message(LOG_CHAT_ID, text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"❌ log_event FAILED (chat={LOG_CHAT_ID}): {type(e).__name__}: {e}")


async def safe_edit(call: CallbackQuery, text: str, kb: InlineKeyboardMarkup):
    try:
        await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        try:
            await call.message.delete()
        except Exception:
            pass
        try:
            await call.message.answer(text, reply_markup=kb, parse_mode="HTML")
        except Exception as e:
            logging.error(f"safe_edit fail: {e}")
