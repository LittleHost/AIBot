# utils.py
from aiogram.types import CallbackQuery, InlineKeyboardMarkup
from config import LOG_CHAT_ID


async def log_event(bot, action: str, user=None, extra: str = ""):
    """Отправка лога в чат логов"""
    if not LOG_CHAT_ID:
        print("⚠️ LOG_CHAT_ID пустой")
        return
    try:
        if user is not None:
            uname = f"@{user.username}" if getattr(user, "username", None) else getattr(user, "first_name", "—")
            uid = getattr(user, "id", "—")
            text = (
                f"📌 <b>Лог</b>\n\n<blockquote>"
                f"👤 {uname}\n"
                f"🆔 <code>{uid}</code>\n"
                f"⚙️ Действие: <b>{action}</b>"
            )
            if extra:
                text += f"\n📝 {extra}"
            text += "</blockquote>"
        else:
            text = (
                f"📌 <b>Лог</b>\n\n<blockquote>"
                f"⚙️ Действие: <b>{action}</b>"
            )
            if extra:
                text += f"\n📝 {extra}"
            text += "</blockquote>"
        await bot.send_message(LOG_CHAT_ID, text, parse_mode="HTML")
    except Exception as e:
        print(f"❌ log_event error: {type(e).__name__}: {e}")


async def safe_edit(call: CallbackQuery, text: str, kb: InlineKeyboardMarkup):
    """Безопасное редактирование"""
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
            print(f"safe_edit fail: {e}")
