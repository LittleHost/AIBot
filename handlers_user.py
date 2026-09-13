# handlers_user.py
import aiosqlite
from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from database import (
    get_user, register_user, get_history, get_transactions,
    get_setting, set_user_setting, get_referrals_count, claim_referral_balance,
    DB_PATH
)
from handlers_checks import process_start_check
from config import EMOJI, ICON_IDS, TOP_NUMBERS
from keyboards import main_kb, games_select_kb
from utils import safe_edit, log_event

user_router = Router()


def is_chat_group(msg: Message) -> bool:
    return msg.chat.type in ["group", "supergroup"]


@user_router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return await message.answer(
            "ℹ️ Нет активных действий для отмены.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_to_main", style="primary")]
            ])
        )
    await state.clear()
    await message.answer(
        "❌ <b>Действие отменено.</b>\n\n"
        "<blockquote>Вы вернулись в главное меню.</blockquote>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_to_main", style="primary")]
        ]),
        parse_mode="HTML"
    )


@user_router.message(CommandStart())
async def on_start(message: Message, bot: Bot):
    if is_chat_group(message):
        bot_info = await message.bot.get_me()
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Открыть в ЛС", url=f"https://t.me/{bot_info.username}?start=help", style="primary", icon_custom_emoji_id=ICON_IDS["rocket"])]
        ])
        return await message.reply(
            f"{EMOJI['star']} <b>Быстрые игры в чате доступны!</b>\n\n"
            f"<blockquote>Команды:\n• <code>игры</code>\n• <code>мины</code> / <code>башня</code>\n"
            f"• <code>баланс</code> / <code>профиль</code> / <code>джекпот</code> / <code>топ</code></blockquote>",
            reply_markup=kb, parse_mode="HTML"
        )
    has_prem = 1 if message.from_user.is_premium else 0
    ref_id = 0
    args = message.text.split()
    if len(args) > 1:
        if args[1].startswith("check_"):
            await register_user(message.from_user.id, message.from_user.username or "", 0, has_prem)
            code = args[1].replace("check_", "").strip()
            return await process_start_check(message, code, bot)
        if args[1].startswith("ref_"):
            try:
                parsed_ref = int(args[1].split("_")[1])
                if parsed_ref != message.from_user.id:
                    ref_id = parsed_ref
            except (ValueError, IndexError):
                pass
    await register_user(message.from_user.id, message.from_user.username or "", ref_id, has_prem)
    await log_event(bot, "🚀 Старт бота", message.from_user,
                    f"Реф: {ref_id}" if ref_id else "Без рефа")
    bot_info = await message.bot.get_me()
    try:
        photo = FSInputFile("start.png")
        text = (
            f"{EMOJI['star']} <b>Привет, добро пожаловать в @{bot_info.username}!</b>\n\n"
            f"<blockquote>Подписывайся на наш канал @nc_bet чтобы следить за новостями и конкурсами!</blockquote>"
        )
        await message.answer_photo(photo=photo, caption=text, reply_markup=main_kb(), parse_mode="HTML")
    except Exception as e:
        print(f"Ошибка загрузки start.png: {e}")
        text = (
            f"{EMOJI['star']} <b>Привет, добро пожаловать в @{bot_info.username}!</b>\n\n"
            f"<blockquote>Подписывайся на наш канал @nc_bet чтобы следить за новостями и конкурсами!</blockquote>"
        )
        await message.answer(text, reply_markup=main_kb(), parse_mode="HTML")


@user_router.message(Command("help"))
async def cmd_help(message: Message):
    text = (
        f"{EMOJI['star']} <b>Помощь</b>\n\n<blockquote>"
        f"<b>Основные команды:</b>\n"
        f"• <code>/start</code> — главное меню\n"
        f"• <code>/help</code> — эта справка\n"
        f"• <code>/cancel</code> — отменить текущее действие\n"
        f"• <code>/send СУММА</code> (reply) — перевод игроку\n\n"
        f"<b>Игровые команды (в чате):</b>\n"
        f"• <code>игры</code> — меню мини-игр\n"
        f"• <code>мины</code> / <code>башня</code> — быстрый запуск\n"
        f"• <code>куб больше</code> / <code>куб 5</code> — быстрые ставки\n"
        f"• <code>баланс</code> / <code>профиль</code> / <code>топ</code>\n"
        f"• <code>джекпот</code> — джекпот чата\n\n"
        f"<b>Прочее:</b>\n"
        f"• <code>/promo КОД</code> — активировать промокод\n"
        f"• <code>/game_off</code> — отменить активную игру\n\n"
        f"<i>Все игры честны (Provably Fair SHA-256).</i>\n"
        f"<i>Удачи 🍀</i></blockquote>"
    )
    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_to_main", style="primary")]
    ]), parse_mode="HTML")


@user_router.callback_query(F.data == "back_to_main")
async def back_to_main(call: CallbackQuery):
    bot_info = await call.bot.get_me()
    text = f"{EMOJI['star']} <b>Главное меню @{bot_info.username}</b>\n\n<blockquote>Подписывайся на наш канал @nc_bet</blockquote>"
    await safe_edit(call, text, main_kb())


@user_router.callback_query(F.data == "open_games")
async def open_games_menu(call: CallbackQuery):
    text = (
        f"{EMOJI['fire']} <b>Игровое меню NiceBet</b>\n\n"
        f"<blockquote>Выбери игру:\n\n"
        f"🎲 Кости — угадай число/чёт/больше\n"
        f"💣 Мины — открой алмазы, не попав на мину\n"
        f"🗼 Башня — поднимайся и забирай банк\n"
        f"⚽ Спорт — ставки на события</blockquote>"
    )
    await safe_edit(call, text, games_select_kb())


RANK_CASHBACK_PERCENT = {"None": 0.0, "Bronze": 3.0, "Silver": 6.0, "Gold": 8.0}


@user_router.callback_query(F.data == "open_cashback")
async def show_cashback_menu(call: CallbackQuery):
    user = await get_user(call.from_user.id)
    rank = user["user_rank"] if user["user_rank"] in RANK_CASHBACK_PERCENT else "None"
    pct = RANK_CASHBACK_PERCENT[rank]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Забрать кешбэк (от 0.1$)", callback_data="claim_cashback_action", style="success", icon_custom_emoji_id=ICON_IDS["cash"])],
        [InlineKeyboardButton(text="Назад", callback_data="back_to_main", style="danger", icon_custom_emoji_id=ICON_IDS["cross"])]
    ])
    text = (
        f"💎 <b>Кэшбек</b>\n\n<blockquote>"
        f"Доступно — <b>{user['cashback_balance']:.2f} 💵</b>\n"
        f"За всё время — <b>{user['cashback_total']:.2f} 💵</b>\n"
        f"Ваш процент: <b>{pct}% ⭐</b>\n\n"
        f"<i>Забрать кешбек можно каждую пятницу с 00:00!</i></blockquote>"
    )
    await safe_edit(call, text, kb)


@user_router.callback_query(F.data == "claim_cashback_action")
async def claim_cashback_process(call: CallbackQuery):
    now_utc = datetime.utcnow()
    if now_utc.weekday() != 4:
        return await call.answer("❌ Забрать кешбэк можно только в пятницу!", show_alert=True)
    user = await get_user(call.from_user.id)
    cb_amt = user["cashback_balance"]
    if cb_amt < 0.10:
        return await call.answer("❌ Кэшбэк меньше 0.1$", show_alert=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET balance = ROUND(balance + ?, 4), cashback_balance = 0.0 WHERE user_id = ?", (cb_amt, call.from_user.id))
        await db.execute("INSERT INTO transactions (user_id, type, amount, gateway, status) VALUES (?, 'cashback', ?, 'internal', 'success')", (call.from_user.id, cb_amt))
        await db.commit()
    await call.answer(f"✅ Зачислено +{cb_amt:.2f}$!", show_alert=True)
    await log_event(call.bot, "💎 Кэшбэк получен", call.from_user, f"+{cb_amt:.2f} $")
    await show_cashback_menu(call)


@user_router.callback_query(F.data == "open_ranks_info")
async def show_ranks_info(call: CallbackQuery):
    user = await get_user(call.from_user.id)
    rank = user["user_rank"] if user["user_rank"] else "None"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад в профиль", callback_data="profile", style="danger", icon_custom_emoji_id=ICON_IDS["cross"])]
    ])
    text = (
        f"{EMOJI['star']} <b>Система уровней</b>\n\n<blockquote>"
        f"{EMOJI['fire']} <b>None</b> — 0$\n"
        f"Bronze — 10,000$ → +15$ (кэшбек 3%)\n"
        f"Silver — 50,000$ → +30$ (кэшбек 6%)\n"
        f"Gold — 100,000$ → +60$ (кэшбек 8%)\n\n"
        f"Ваш ранг: <b>{rank}</b></blockquote>"
    )
    await safe_edit(call, text, kb)


async def get_private_profile_data(user_id: int, first_name: str, username: str):
    user = await get_user(user_id)
    if user['display_mode'] == "username" and user['username']:
        name = f"@{user['username']}"
    elif user['display_mode'] == "anon":
        name = "🕶️ Аноним"
    else:
        name = first_name
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Пополнить", callback_data="profile_dep", style="success", icon_custom_emoji_id=ICON_IDS["cash"]),
            InlineKeyboardButton(text="Вывести", callback_data="profile_w", style="danger", icon_custom_emoji_id=ICON_IDS["cash"])
        ],
        [
            InlineKeyboardButton(text="Чеки", callback_data="open_checks_menu", style="primary", icon_custom_emoji_id=ICON_IDS["cash"]),
            InlineKeyboardButton(text="За уровень", callback_data="open_ranks_info", style="primary", icon_custom_emoji_id=ICON_IDS["star"])
        ],
        [InlineKeyboardButton(text="История игр (7 дней)", callback_data="view_history_games", style="primary", icon_custom_emoji_id=ICON_IDS["trophy"])],
        [InlineKeyboardButton(text="История транзакций", callback_data="view_history_tx")],
        [InlineKeyboardButton(text="Сменить отображение ника", callback_data="change_display_mode")],
        [InlineKeyboardButton(text="Главное меню", callback_data="back_to_main", style="danger", icon_custom_emoji_id=ICON_IDS["cross"])]
    ])
    text = (
        f"{EMOJI['trophy']} <b>Игровой профиль</b>\n\n<blockquote>"
        f"Пользователь: <b>{name}</b>\n"
        f"Ранг: <b>{user['user_rank'] or 'None'}</b>\n"
        f"ID: <code>{user['user_id']}</code>\n"
        f"Баланс: <b>{user['balance']:.2f}</b> {EMOJI['cash']}\n"
        f"Оборот: <b>{user['turnover']:.2f}</b> {EMOJI['cash']}\n"
        f"Дата: <b>{user['reg_date']}</b></blockquote>"
    )
    return text, kb


@user_router.callback_query(F.data == "profile")
async def on_profile_cb(call: CallbackQuery):
    text, kb = await get_private_profile_data(call.from_user.id, call.from_user.first_name, call.from_user.username)
    try:
        photo = FSInputFile("profile.png")
        try:
            await call.message.delete()
        except Exception:
            pass
        await call.message.answer_photo(photo=photo, caption=text, reply_markup=kb, parse_mode="HTML")
    except Exception as e:
        print(f"profile.png err: {e}")
        await safe_edit(call, text, kb)


@user_router.message(F.text.lower().in_(["профиль", "/profile"]))
async def on_profile_msg(message: Message):
    uid = message.from_user.id
    user = await get_user(uid)
    bot_info = await message.bot.get_me()
    if is_chat_group(message):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Пополнить в боте", url=f"https://t.me/{bot_info.username}?start=dep", style="success", icon_custom_emoji_id=ICON_IDS["cash"])]
        ])
        text = (
            f"{EMOJI['trophy']} <b>Профиль {message.from_user.first_name}</b>\n\n"
            f"<blockquote>ID: <code>{user['user_id']}</code>\n"
            f"Ранг: <b>{user['user_rank'] or 'None'}</b>\n"
            f"Баланс: <b>{user['balance']:.2f}</b> {EMOJI['cash']}\n"
            f"Оборот: <b>{user['turnover']:.2f}</b> {EMOJI['cash']}</blockquote>"
        )
        return await message.reply(text, reply_markup=kb, parse_mode="HTML")
    text, kb = await get_private_profile_data(uid, message.from_user.first_name, message.from_user.username)
    try:
        photo = FSInputFile("profile.png")
        await message.answer_photo(photo=photo, caption=text, reply_markup=kb, parse_mode="HTML")
    except Exception as e:
        print(f"profile.png err: {e}")
        await message.answer(text, reply_markup=kb, parse_mode="HTML")


@user_router.message(F.text.lower().in_(["баланс", "/balance", "bal"]))
async def on_balance_msg(message: Message):
    user = await get_user(message.from_user.id)
    bot_info = await message.bot.get_me()
    if is_chat_group(message):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Пополнить", url=f"https://t.me/{bot_info.username}?start=dep", style="success", icon_custom_emoji_id=ICON_IDS["cash"])]
        ])
        return await message.reply(
            f"{EMOJI['cash']} <b>Баланс {message.from_user.first_name}:</b> <code>{user['balance']:.2f} $</code>",
            reply_markup=kb, parse_mode="HTML"
        )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Пополнить", callback_data="profile_dep", style="success", icon_custom_emoji_id=ICON_IDS["cash"]),
            InlineKeyboardButton(text="Вывести", callback_data="profile_w", style="danger", icon_custom_emoji_id=ICON_IDS["cash"])
        ]
    ])
    await message.reply(f"{EMOJI['cash']} <b>Ваш баланс:</b> <code>{user['balance']:.2f} $</code>", reply_markup=kb, parse_mode="HTML")


@user_router.callback_query(F.data == "change_display_mode")
async def choose_nick_mode(call: CallbackQuery):
    user_first_name = call.from_user.first_name
    username_text = f"@{call.from_user.username}" if call.from_user.username else "Нет username"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"👤 {user_first_name}", callback_data="set_disp_first_name", style="primary")],
        [InlineKeyboardButton(text=f"🏷 {username_text}", callback_data="set_disp_username", style="primary")],
        [InlineKeyboardButton(text="🕶️ Аноним", callback_data="set_disp_anon", style="primary")],
        [InlineKeyboardButton(text="Назад в профиль", callback_data="profile", style="danger", icon_custom_emoji_id=ICON_IDS["cross"])]
    ])
    await safe_edit(call, "✏️ <b>Выберите как отображаться:</b>", kb)


@user_router.callback_query(F.data.startswith("set_disp_"))
async def save_disp_mode(call: CallbackQuery):
    mode = call.data.replace("set_disp_", "")
    await set_user_setting(call.from_user.id, "display_mode", mode)
    await call.answer("✅ Обновлено!", show_alert=True)
    await log_event(call.bot, "✏️ Смена отображения", call.from_user, f"Режим: {mode}")
    text, kb = await get_private_profile_data(call.from_user.id, call.from_user.first_name, call.from_user.username)
    await safe_edit(call, text, kb)


@user_router.callback_query(F.data == "view_history_games")
async def view_games(call: CallbackQuery):
    rows = await get_history(call.from_user.id, days=7)
    if not rows:
        return await call.answer("История за 7 дней пуста.", show_alert=True)
    lines = ["📜 <b>История игр:</b>\n<blockquote>"]
    for r in rows:
        st = "🟢 +" if r["win"] else "🔴 -"
        v = r["payout"] if r["win"] else r["bet"]
        lines.append(f"{st}{v:.2f}$ | {r['game_name']} | {r['created_at'].split()[0]}")
    lines.append("</blockquote>")
    await call.message.answer("\n".join(lines), parse_mode="HTML")
    await call.answer()


@user_router.callback_query(F.data == "view_history_tx")
async def view_transactions(call: CallbackQuery):
    rows = await get_transactions(call.from_user.id)
    if not rows:
        return await call.answer("История транзакций пуста.", show_alert=True)
    lines = ["📊 <b>Последние транзакции:</b>\n<blockquote>"]
    for r in rows:
        emoji = "🟢" if r["status"] == "success" else "🔴"
        lines.append(f"{emoji} {r['type'].upper()}: {r['amount']:.2f}$ ({r['gateway']}) | {r['created_at'].split()[0]}")
    lines.append("</blockquote>")
    await call.message.answer("\n".join(lines), parse_mode="HTML")
    await call.answer()


@user_router.callback_query(F.data == "referrals")
async def on_referrals(call: CallbackQuery):
    user = await get_user(call.from_user.id)
    bot_info = await call.bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{user['user_id']}"
    ref_count = await get_referrals_count(user['user_id'])
    kb = []
    if user["ref_balance"] > 0:
        kb.append([InlineKeyboardButton(text=f"Забрать {user['ref_balance']:.2f} $", callback_data="claim_ref_reward", style="success", icon_custom_emoji_id=ICON_IDS["cash"])])
    kb.append([InlineKeyboardButton(text="Назад", callback_data="back_to_main", style="danger", icon_custom_emoji_id=ICON_IDS["cross"])])
    text = (
        f"{EMOJI['cash']} <b>Реферальная программа</b>\n\n<blockquote>"
        f"Приглашайте и получайте <b>5%</b> с проигрышей!\n\n"
        f"👥 Приглашено: <b>{ref_count}</b>\n"
        f"💵 Доход: <b>{user['ref_balance']:.2f}</b> $\n\n"
        f"Ваша ссылка:\n<code>{ref_link}</code></blockquote>"
    )
    try:
        photo = FSInputFile("ref.png")
        try:
            await call.message.delete()
        except Exception:
            pass
        await call.message.answer_photo(photo=photo, caption=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")
    except Exception as e:
        print(f"ref.png err: {e}")
        await safe_edit(call, text, InlineKeyboardMarkup(inline_keyboard=kb))


@user_router.callback_query(F.data == "claim_ref_reward")
async def claim_ref_bonus(call: CallbackQuery):
    claimed = await claim_referral_balance(call.from_user.id)
    if claimed <= 0:
        return await call.answer("❌ На реф-балансе нет средств.", show_alert=True)
    await call.answer(f"✅ +{claimed:.2f}$ на баланс!", show_alert=True)
    await log_event(call.bot, "👥 Реф-бонус получен", call.from_user, f"+{claimed:.2f} $")
    await on_referrals(call)


@user_router.callback_query(F.data == "open_chats")
async def on_chats(call: CallbackQuery):
    chat_link = await get_setting("chat_link")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Перейти в чат", url=chat_link, style="primary")],
        [InlineKeyboardButton(text="Назад", callback_data="back_to_main", style="danger", icon_custom_emoji_id=ICON_IDS["cross"])]
    ])
    await safe_edit(call, "💬 <b>Наши игровые чаты:</b>", kb)


@user_router.callback_query(F.data == "rules")
async def on_rules(call: CallbackQuery):
    text = (
        f"{EMOJI['gem']} <b>Правила казино</b>\n\n<blockquote>"
        f"1. Вывод доступен в любое время.\n"
        f"2. Скрипты/баги = блокировка.\n"
        f"3. Игры честны (SHA-256).</blockquote>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад", callback_data="back_to_main", style="danger", icon_custom_emoji_id=ICON_IDS["cross"])]
    ])
    await safe_edit(call, text, kb)


@user_router.message(Command("promo"))
async def activate_promo(message: Message):
    args = message.text.split()
    if len(args) < 2:
        return await message.reply("⚠️ Пример: <code>/promo СЕКРЕТ</code>", parse_mode="HTML")
    code = args[1].strip()
    uid = message.from_user.id
    user = await get_user(uid)
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM promos WHERE code = ?", (code,)) as cur:
            promo = await cur.fetchone()
        if not promo or promo["activations_left"] <= 0:
            return await message.reply("❌ Промокод не существует или закончился!")
        async with db.execute("SELECT 1 FROM promo_activations WHERE code = ? AND user_id = ?", (code, uid)) as cur:
            if await cur.fetchone():
                return await message.reply("❌ Вы уже активировали!")
        if promo["only_premium"] and not message.from_user.is_premium:
            return await message.reply("❌ Только для Premium!")
        if user["turnover"] < promo["min_turnover"]:
            return await message.reply(f"❌ Оборот от {promo['min_turnover']:.2f}$!")
        if user["deposits_sum"] < promo["min_deposits_sum"]:
            return await message.reply(f"❌ Депозитов от {promo['min_deposits_sum']:.2f}$!")
        await db.execute("UPDATE promos SET activations_left = activations_left - 1 WHERE code = ?", (code,))
        await db.execute("INSERT INTO promo_activations (code, user_id) VALUES (?, ?)", (code, uid))
        await db.execute("UPDATE users SET balance = ROUND(balance + ?, 4) WHERE user_id = ?", (promo["reward"], uid))
        await db.commit()
    await log_event(message.bot, "🎁 Промокод активирован", message.from_user,
                    f"Код: <code>{code}</code>\n+{promo['reward']:.2f} $")
    await message.reply(f"🎉 <b>Промокод активирован!</b>\n<blockquote>+{promo['reward']:.2f} $</blockquote>", parse_mode="HTML")