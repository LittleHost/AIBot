# bot.py — точка входа
import asyncio
import logging
import aiosqlite
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Update, BotCommand, BotCommandScopeDefault

from config import BOT_TOKEN, LOG_CHAT_ID, DB_PATH
from database import init_db
from middlewares import ThrottlingMiddleware
from cryptopay import cb_check_stat

from handlers_user import user_router
from handlers_chat import chat_router
from handlers_finance import finance_router
from handlers_checks import checks_router
from handlers_admin import admin_router
from handlers_sport_admin import admin_sport_router
from handlers_sport import sport_router
from handlers_games import games_router
from handlers_quick import quick_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s")


async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="🏠 Главное меню"),
        BotCommand(command="help", description="ℹ️ Помощь"),
        BotCommand(command="cancel", description="❌ Отменить действие"),
        BotCommand(command="send", description="💸 Перевод игроку"),
    ]
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())


async def auto_check_invoices(bot: Bot):
    """Фоновая проверка пополнений каждые 30 секунд"""
    while True:
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("SELECT * FROM invoices WHERE status = 'active'") as cur:
                    invoices = await cur.fetchall()

            for inv in invoices:
                try:
                    res = await cb_check_stat(int(inv["invoice_id"]))
                    if res == "paid":
                        async with aiosqlite.connect(DB_PATH) as db:
                            await db.execute("UPDATE invoices SET status = 'paid' WHERE invoice_id = ?", (inv["invoice_id"],))
                            total_amount = inv["amount"] + inv["bonus_amount"]
                            await db.execute("""
                            UPDATE users SET balance = ROUND(balance + ?, 4), deposits_sum = ROUND(deposits_sum + ?, 4),
                                             deposits_count = deposits_count + 1, wager_required = ROUND(wager_required + ?, 4)
                            WHERE user_id = ?
                            """, (total_amount, inv["amount"], inv["wager_required"], inv["user_id"]))
                            await db.execute("INSERT INTO transactions (user_id, type, amount, gateway, status) VALUES (?, 'deposit', ?, 'cryptobot', 'success')",
                                             (inv["user_id"], inv["amount"]))
                            await db.commit()

                        # Уведомляем юзера
                        try:
                            await bot.send_message(
                                inv["user_id"],
                                f"✅ <b>Пополнение зачислено автоматически!</b>\n\n"
                                f"<blockquote>Сумма: <b>+{inv['amount']:.2f} $</b>\n"
                                f"Бонус: <b>+{inv['bonus_amount']:.2f} $</b>\n"
                                f"Отыгрыш: <b>{inv['wager_required']:.2f} $</b></blockquote>",
                                parse_mode="HTML"
                            )
                        except Exception:
                            pass

                        # Логируем
                        try:
                            from utils import log_event
                            await log_event(bot, "Авто-пополнение", None,
                                            f"Юзер: <code>{inv['user_id']}</code> | +{inv['amount']:.2f} $ | Бонус: +{inv['bonus_amount']:.2f} $")
                        except Exception as e:
                            logging.error(f"log_event error: {e}")

                        logging.info(f"✅ Автопополнение: юзер {inv['user_id']}, +{inv['amount']:.2f} $")
                except Exception as e:
                    logging.error(f"Auto-check error для {inv['invoice_id']}: {e}")
        except Exception as e:
            logging.error(f"Auto-check loop error: {e}")

        await asyncio.sleep(30)


async def main():
    await init_db()
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    dp.message.middleware(ThrottlingMiddleware())
    dp.callback_query.middleware(ThrottlingMiddleware())

    @dp.update.outer_middleware()
    async def debug_updates(handler, event: Update, data: dict):
        if event.message:
            logging.info(f"📥 @{event.message.from_user.username or event.message.from_user.id}: {event.message.text}")
        return await handler(event, data)

    dp.include_router(admin_router)
    dp.include_router(admin_sport_router)
    dp.include_router(finance_router)
    dp.include_router(checks_router)
    dp.include_router(games_router)
    dp.include_router(sport_router)
    dp.include_router(chat_router)
    dp.include_router(quick_router)
    dp.include_router(user_router)

    await bot.delete_webhook(drop_pending_updates=True)
    await set_bot_commands(bot)

    # === ТЕСТ ЛОГОВ ===
    logging.info(f"🔍 LOG_CHAT_ID = {LOG_CHAT_ID}")
    try:
        test_msg = await bot.send_message(
            LOG_CHAT_ID,
            "🚀 <b>Тест логов</b>\n\n<blockquote>Бот запущен, логи работают!</blockquote>",
            parse_mode="HTML"
        )
        logging.info(f"✅ ТЕСТ логов: отправлено msg_id={test_msg.message_id}")
    except Exception as e:
        logging.error(f"❌ ТЕСТ логов провалился: {type(e).__name__}: {e}")
        logging.error(f"❌ Chat ID = {LOG_CHAT_ID}")

    # === АВТОПОПОЛНЕНИЕ ===
    asyncio.create_task(auto_check_invoices(bot))
    logging.info("🔄 Автопополнение запущено (каждые 30 сек)")

    bot_info = await bot.get_me()
    logging.info(f"🤖 Бот запущен: @{bot_info.username} (ID: {bot_info.id})")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен.")
