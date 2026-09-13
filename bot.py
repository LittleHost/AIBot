# bot.py — точка входа
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Update, BotCommand, BotCommandScopeDefault

from config import BOT_TOKEN
from database import init_db
from middlewares import ThrottlingMiddleware, ChatLinkMiddleware

from handlers_user import user_router
from handlers_chat import chat_router
from handlers_finance import finance_router, background_invoice_checker
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


async def main():
    await init_db()
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    dp.message.middleware(ThrottlingMiddleware())
    dp.callback_query.middleware(ThrottlingMiddleware())
    dp.message.middleware(ChatLinkMiddleware())

    @dp.update.outer_middleware()
    async def debug_updates(handler, event: Update, data: dict):
        if event.message:
            logging.info(f"📥 @{event.message.from_user.username or event.message.from_user.id}: {event.message.text}")
        return await handler(event, data)

    # Порядок важен!
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

    bot_info = await bot.get_me()
    logging.info(f"🤖 Бот запущен: @{bot_info.username} (ID: {bot_info.id})")

    # Фоновый таск автопроверки инвойсов (автоподтверждение пополнений)
    asyncio.create_task(background_invoice_checker(bot))

    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен.")
