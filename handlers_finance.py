# handlers_finance.py
import aiosqlite
import math
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import get_user, update_balance, get_setting, DB_PATH
from cryptopay import cb_create_invoice, cb_check_stat, cb_create_check
from config import ADMIN_IDS, EMOJI, ICON_IDS
from utils import safe_edit, log_event

finance_router = Router()

MIN_DEPOSIT = 0.10
MIN_WITHDRAW_USER = 1.00
MIN_WITHDRAW_ADMIN = 0.10
WAGER_PERCENT = 0.10


class FinanceStates(StatesGroup):
    waiting_for_deposit_amount = State()
    waiting_for_withdraw_amount = State()


def dep_gateways_kb(amount: float) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"💰 Пополнить ({amount:.2f}$)", callback_data=f"dep_gw_cb_{amount}", style="success", icon_custom_emoji_id=ICON_IDS["cash"])],
        [InlineKeyboardButton(text="Отмена", callback_data="cancel_finance_state", style="danger", icon_custom_emoji_id=ICON_IDS["cross"])]
    ])


def withdraw_gateways_kb(amount: float) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏦 CryptoBot Чек", callback_data=f"w_gw_cb_{amount}", style="success", icon_custom_emoji_id=ICON_IDS["cash"])],
        [InlineKeyboardButton(text="Отмена", callback_data="cancel_finance_state", style="danger", icon_custom_emoji_id=ICON_IDS["cross"])]
    ])


def cancel_action_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Отмена", callback_data="cancel_finance_state", style="danger", icon_custom_emoji_id=ICON_IDS["cross"])]
    ])


@finance_router.callback_query(F.data == "cancel_finance_state")
async def cancel_finance(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await safe_edit(call, "❌ Операция отменена.",
                    InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="В меню", callback_data="back_to_main", style="primary")]]))


@finance_router.callback_query(F.data == "profile_dep")
async def ask_deposit_amount(call: CallbackQuery, state: FSMContext):
    user = await get_user(call.from_user.id)
    if user and user["ban_deposits"]:
        return await call.answer("❌ Пополнения заблокированы.", show_alert=True)
    gw_status = await get_setting("gateway_cryptobot", "1")
    if gw_status != "1":
        return await call.answer("❌ Пополнения временно отключены.", show_alert=True)
    await state.set_state(FinanceStates.waiting_for_deposit_amount)
    text = (
        f"📥 <b>Пополнение</b>\n\n"
        f"<blockquote>Введите сумму в $:\nМинимум: <b>{MIN_DEPOSIT:.2f} $</b>\n\n"
        f"<i>💡 Бонус 10% нужно отыграть перед выводом.</i></blockquote>"
    )
    await safe_edit(call, text, cancel_action_kb())


@finance_router.message(FinanceStates.waiting_for_deposit_amount)
async def process_deposit_input(message: Message, state: FSMContext):
    raw_val = message.text.replace("$", "").replace(",", ".").strip()
    try:
        amount = float(raw_val)
        if math.isnan(amount) or math.isinf(amount) or amount < MIN_DEPOSIT:
            return await message.reply(f"❌ Минимум: <b>{MIN_DEPOSIT:.2f} $</b>", parse_mode="HTML")
        amount = round(amount, 2)
    except ValueError:
        return await message.reply("❌ Число:")
    await state.clear()
    await message.reply(
        f"📥 <b>Пополнение: {amount:.2f} $</b>\n\n<blockquote>Нажмите кнопку ниже:</blockquote>",
        reply_markup=dep_gateways_kb(amount), parse_mode="HTML"
    )


@finance_router.callback_query(F.data.startswith("dep_gw_cb_"))
async def cb_dep_call(call: CallbackQuery):
    amount = float(call.data.split("_")[3])
    await process_deposit(call, amount)


async def process_deposit(call: CallbackQuery, amount: float):
    inv = await cb_create_invoice(amount, call.from_user.id)
    if not inv:
        return await call.answer("❌ Ошибка CryptoBot API. Проверьте токен.", show_alert=True)
    inv_id = str(inv["invoice_id"])
    bonus_amount = round(amount * WAGER_PERCENT, 2)
    wager_required = bonus_amount
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO invoices (invoice_id, user_id, amount, gateway, status, bonus_type, bonus_amount, wager_required) VALUES (?, ?, ?, 'cryptobot', 'active', 'normal', ?, ?)",
            (inv_id, call.from_user.id, amount, bonus_amount, wager_required)
        )
        await db.commit()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить", url=inv["bot_invoice_url"], style="success", icon_custom_emoji_id=ICON_IDS["cash"])],
        [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data=f"chk_inv_cb_{inv_id}", style="primary")]
    ])
    text = (
        f"📥 <b>Счёт CryptoBot создан</b>\n\n<blockquote>"
        f"Сумма: <b>{amount:.2f} USDT</b>\n"
        f"Бонус: <b>+{bonus_amount:.2f} $</b>\n"
        f"Отыгрыш: <b>{wager_required:.2f} $</b>\n"
        f"ID: <code>{inv_id}</code></blockquote>"
    )
    await safe_edit(call, text, kb)


@finance_router.callback_query(F.data.startswith("chk_inv_"))
async def check_invoice_status_callback(call: CallbackQuery, bot: Bot):
    parts = call.data.split("_")
    gw, inv_id = parts[2], parts[3]
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM invoices WHERE invoice_id = ?", (inv_id,)) as cur:
            inv = await cur.fetchone()
    if not inv:
        return await call.answer("❌ Счёт не найден.", show_alert=True)
    if inv["status"] == "paid":
        return await call.answer("✅ Уже оплачен!", show_alert=True)
    if inv["status"] == "processing":
        return await call.answer("⏳ Проверяется...", show_alert=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE invoices SET status = 'processing' WHERE invoice_id = ?", (inv_id,))
        await db.commit()
    is_paid = False
    if gw == "cb":
        res = await cb_check_stat(int(inv_id))
        is_paid = (res == "paid")
    async with aiosqlite.connect(DB_PATH) as db:
        if is_paid:
            await db.execute("UPDATE invoices SET status = 'paid' WHERE invoice_id = ?", (inv_id,))
            total_amount = inv["amount"] + inv["bonus_amount"]
            await db.execute("""
            UPDATE users SET balance = ROUND(balance + ?, 4), deposits_sum = ROUND(deposits_sum + ?, 4),
                             deposits_count = deposits_count + 1, wager_required = ROUND(wager_required + ?, 4)
            WHERE user_id = ?
            """, (total_amount, inv["amount"], inv["wager_required"], inv["user_id"]))
            await db.execute("INSERT INTO transactions (user_id, type, amount, gateway, status) VALUES (?, 'deposit', ?, ?, 'success')",
                             (inv["user_id"], inv["amount"], gw))
            if inv["bonus_amount"] > 0:
                await db.execute("INSERT INTO transactions (user_id, type, amount, gateway, status) VALUES (?, 'bonus', ?, ?, 'success')",
                                 (inv["user_id"], inv["bonus_amount"], gw))
            await db.commit()
            bonus_text = f"Бонус: +{inv['bonus_amount']:.2f} $" if inv["bonus_amount"] > 0 else ""
            text = (
                f"✅ <b>Оплата подтверждена!</b>\n\n<blockquote>"
                f"Зачислено: <b>+{inv['amount']:.2f} $</b>\n{bonus_text}\n"
                f"Отыгрыш: <b>{inv['wager_required']:.2f} $</b></blockquote>"
            )
            await safe_edit(call, text, InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="В меню", callback_data="back_to_main", style="primary")]
            ]))
            await log_event(bot, "Пополнение баланса",
                            call.from_user,
                            f"Сумма: +{inv['amount']:.2f} $\nБонус: +{inv['bonus_amount']:.2f} $\nОтыгрыш: {inv['wager_required']:.2f} $")
        else:
            await db.execute("UPDATE invoices SET status = 'active' WHERE invoice_id = ?", (inv_id,))
            await db.commit()
            return await call.answer("❌ Оплата не подтверждена.", show_alert=True)


@finance_router.callback_query(F.data == "profile_w")
async def ask_withdraw_amount(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    user = await get_user(uid)
    min_limit = MIN_WITHDRAW_ADMIN if uid in ADMIN_IDS else MIN_WITHDRAW_USER
    if user["ban_withdraws"]:
        return await call.answer("❌ Вывод заблокирован.", show_alert=True)
    if user["deposits_sum"] < 1.0:
        return await call.answer(f"❌ Нужен депозит от 1$. Ваш: {user['deposits_sum']:.2f}$", show_alert=True)
    if user["wager_required"] > 0:
        return await call.answer(f"❌ Отыграйте {user['wager_required']:.2f}$!", show_alert=True)
    if user["balance"] < min_limit:
        return await call.answer(f"❌ Минимум: {min_limit:.2f} $", show_alert=True)
    await state.set_state(FinanceStates.waiting_for_withdraw_amount)
    text = (
        f"📤 <b>Вывод средств</b>\n\n<blockquote>Баланс: <b>{user['balance']:.2f} $</b>\n"
        f"Отыгрыш: <b>{user['wager_required']:.2f} $</b>\n"
        f"Введите сумму (мин. <b>{min_limit:.2f} $</b>):</blockquote>"
    )
    await safe_edit(call, text, cancel_action_kb())


@finance_router.message(FinanceStates.waiting_for_withdraw_amount)
async def process_withdraw_input(message: Message, state: FSMContext):
    raw_val = message.text.replace("$", "").replace(",", ".").strip()
    uid = message.from_user.id
    user = await get_user(uid)
    min_limit = MIN_WITHDRAW_ADMIN if uid in ADMIN_IDS else MIN_WITHDRAW_USER
    if user["deposits_sum"] < 1.0:
        return await message.reply("❌ Нужен депозит от 1$!")
    if user["wager_required"] > 0:
        return await message.reply(f"❌ Отыграйте {user['wager_required']:.2f}$!")
    try:
        amount = float(raw_val)
        if math.isnan(amount) or math.isinf(amount) or amount < min_limit:
            return await message.reply(f"❌ Минимум: <b>{min_limit:.2f} $</b>", parse_mode="HTML")
        amount = round(amount, 2)
        if amount > user["balance"]:
            return await message.reply(f"❌ Баланс: <b>{user['balance']:.2f} $</b>", parse_mode="HTML")
    except ValueError:
        return await message.reply("❌ Число:")
    await state.clear()
    await message.reply(
        f"📤 <b>Вывод: {amount:.2f} $</b>\n\n<blockquote>Выберите способ:</blockquote>",
        reply_markup=withdraw_gateways_kb(amount), parse_mode="HTML"
    )


@finance_router.callback_query(F.data.startswith("w_gw_"))
async def on_withdraw_choice(call: CallbackQuery, bot: Bot):
    parts = call.data.split("_")
    gw, amount = parts[2], float(parts[3])
    uid = call.from_user.id
    user = await get_user(uid)
    if user["deposits_sum"] < 1.0:
        return await call.answer("❌ Нужен депозит от 1$!", show_alert=True)
    if user["wager_required"] > 0:
        return await call.answer(f"❌ Отыграйте {user['wager_required']:.2f}$!", show_alert=True)
    if user["balance"] < amount:
        return await call.answer("❌ Недостаточно средств!", show_alert=True)
    mode = await get_setting("withdraw_mode", "manual")
    if mode == "auto":
        await safe_edit(call, "⏳ Создаю чек...", InlineKeyboardMarkup(inline_keyboard=[]))
        link = None
        if gw == "cb":
            check = await cb_create_check(amount)
            if check and check.get("bot_check_url"):
                link = check["bot_check_url"]
        if not link:
            return await safe_edit(call,
                f"❌ <b>Ошибка создания чека!</b>\n\n"
                f"<blockquote>Проверьте баланс CryptoBot и сумму (мин. 0.10 USDT)</blockquote>",
                InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="В меню", callback_data="back_to_main", style="primary")]])
            )
        await update_balance(uid, -amount)
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET withdrawals_sum = ROUND(withdrawals_sum + ?, 4) WHERE user_id = ?", (amount, uid))
            await db.execute("INSERT INTO transactions (user_id, type, amount, gateway, status) VALUES (?, 'withdraw', ?, ?, 'success')", (uid, amount, gw))
            await db.commit()
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💰 Забрать средства", url=link, style="success", icon_custom_emoji_id=ICON_IDS["cash"])]
        ])
        text = f"✅ <b>Вывод выполнен!</b>\n\n<blockquote>Сумма: <b>{amount:.2f} $</b>\nШлюз: <b>CryptoBot</b></blockquote>"
        await safe_edit(call, text, kb)
        await log_event(bot, "Вывод (авто)", call.from_user, f"Сумма: -{amount:.2f} $")
        return
    await update_balance(uid, -amount)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("INSERT INTO withdraw_requests (user_id, amount, gateway, status) VALUES (?, ?, ?, 'pending')", (uid, amount, gw))
        req_id = cur.lastrowid
        await db.commit()
    text = (
        f"📨 <b>Заявка #{req_id} отправлена!</b>\n\n<blockquote>"
        f"Сумма: <b>{amount:.2f} $</b>\nСтатус: ⏳ Ожидает</blockquote>"
    )
    await safe_edit(call, text, InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="В меню", callback_data="back_to_main", style="primary")]
    ]))
    adm_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"adm_pay_ok_{req_id}", style="success"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"adm_pay_cancel_{req_id}", style="danger")
        ]
    ])
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"🔔 <b>Заявка на вывод #{req_id}</b>\n\n<blockquote>"
                f"👤 Игрок: <code>{uid}</code>\n💰 Сумма: <b>{amount:.2f} $</b>\n"
                f"🏦 Шлюз: <b>CryptoBot</b></blockquote>",
                reply_markup=adm_kb, parse_mode="HTML"
            )
        except Exception as e:
            print(f"Ошибка отправки админу: {e}")
    await log_event(bot, "Заявка на вывод создана", call.from_user, f"Сумма: {amount:.2f} $ (заявка #{req_id})")


@finance_router.callback_query(F.data.startswith("adm_pay_ok_"))
async def admin_approve_withdraw(call: CallbackQuery, bot: Bot):
    req_id = int(call.data.split("_")[3])
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM withdraw_requests WHERE id = ?", (req_id,)) as cur:
            req = await cur.fetchone()
    if not req or req["status"] != "pending":
        return await call.answer("❌ Заявка уже обработана.", show_alert=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE withdraw_requests SET status = 'approved' WHERE id = ?", (req_id,))
        await db.commit()
    uid = req["user_id"]
    amount = req["amount"]
    gw = req["gateway"]
    link = None
    if gw == "cb":
        check = await cb_create_check(amount)
        if check and check.get("bot_check_url"):
            link = check["bot_check_url"]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET withdrawals_sum = ROUND(withdrawals_sum + ?, 4) WHERE user_id = ?", (amount, uid))
        await db.execute("INSERT INTO transactions (user_id, type, amount, gateway, status) VALUES (?, 'withdraw', ?, ?, 'success')", (uid, amount, gw))
        await db.commit()
    if link:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💰 Забрать", url=link, style="success", icon_custom_emoji_id=ICON_IDS["cash"])]
        ])
        await safe_edit(call,
            f"✅ <b>Заявка #{req_id} одобрена!</b>\n\n"
            f"<blockquote>Сумма: <b>{amount:.2f} $</b>\nШлюз: <b>CryptoBot</b></blockquote>",
            kb
        )
        try:
            await bot.send_message(
                uid,
                f"🎉 <b>Заявка #{req_id} одобрена!</b>\n\n"
                f"<blockquote>Сумма: <b>{amount:.2f} $</b></blockquote>",
                reply_markup=kb, parse_mode="HTML"
            )
        except Exception:
            pass
    else:
        await safe_edit(call,
            f"⚠️ <b>Заявка #{req_id} одобрена, но чек не создан!</b>\n\n"
            f"<blockquote>Проверьте баланс CryptoBot.</blockquote>",
            InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="OK", callback_data="adm_main_menu", style="primary")]])
        )
    await log_event(bot, "Вывод одобрен", call.from_user, f"Заявка #{req_id}, сумма {amount:.2f} $")


@finance_router.callback_query(F.data.startswith("adm_pay_cancel_"))
async def admin_cancel_withdraw(call: CallbackQuery, bot: Bot):
    req_id = int(call.data.split("_")[3])
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM withdraw_requests WHERE id = ?", (req_id,)) as cur:
            req = await cur.fetchone()
    if not req or req["status"] != "pending":
        return await call.answer("❌ Уже обработана.", show_alert=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE withdraw_requests SET status = 'cancelled' WHERE id = ?", (req_id,))
        await db.execute("UPDATE users SET balance = ROUND(balance + ?, 4) WHERE user_id = ?", (req["amount"], req["user_id"]))
        await db.commit()
    uid = req["user_id"]
    amount = req["amount"]
    await safe_edit(call,
        f"❌ <b>Заявка #{req_id} отклонена!</b>\n\n"
        f"<blockquote>Возвращено <b>{amount:.2f} $</b> игроку.</blockquote>",
        InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="OK", callback_data="adm_main_menu", style="primary")]])
    )
    try:
        await bot.send_message(
            uid,
            f"❌ <b>Заявка #{req_id} отклонена.</b>\n\n"
            f"<blockquote>Сумма <b>{amount:.2f} $</b> возвращена.</blockquote>",
            parse_mode="HTML"
        )
    except Exception:
        pass
    await log_event(bot, "Вывод отклонён", call.from_user, f"Заявка #{req_id}, сумма {amount:.2f} $")