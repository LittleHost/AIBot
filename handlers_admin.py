# handlers_admin.py
import asyncio
import aiosqlite
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import (
    get_user, get_all_user_ids, create_promo_code, reset_top_statistics,
    get_setting, set_setting, admin_user_action, get_transactions,
    get_referrals_count, DB_PATH
)
from config import ADMIN_IDS, EMOJI, ICON_IDS
from utils import safe_edit, log_event

admin_router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


class AdminStates(StatesGroup):
    # Общие
    waiting_for_user_id = State()
    waiting_for_broadcast_text = State()
    waiting_for_promo_code = State()
    waiting_for_promo_reward = State()
    # Управление игроком
    adm_find_id = State()
    adm_add_balance = State()
    adm_sub_balance = State()
    adm_set_balance = State()
    adm_set_rank = State()
    adm_set_turnover = State()
    adm_msg_to_user = State()


def admin_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Управление игроком", callback_data="adm_player_menu", style="primary", icon_custom_emoji_id=ICON_IDS["rocket"])],
        [
            InlineKeyboardButton(text="🎁 Создать промокод", callback_data="adm_create_promo", style="success", icon_custom_emoji_id=ICON_IDS["cash"]),
            InlineKeyboardButton(text="⚽ Спорт", callback_data="adm_sport_menu", style="primary", icon_custom_emoji_id=ICON_IDS["fire"])
        ],
        [
            InlineKeyboardButton(text="📢 Рассылка", callback_data="adm_broadcast_start", style="primary", icon_custom_emoji_id=ICON_IDS["fire"]),
            InlineKeyboardButton(text="📊 Статистика", callback_data="adm_stats", style="primary")
        ],
        [
            InlineKeyboardButton(text="💳 Шлюзы", callback_data="adm_gateways_menu", style="primary"),
            InlineKeyboardButton(text="♻️ Сбросить ТОП", callback_data="adm_reset_top", style="danger")
        ]
    ])


@admin_router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.reply("⚙️ <b>Панель администратора:</b>", reply_markup=admin_main_kb(), parse_mode="HTML")


@admin_router.callback_query(F.data == "adm_main_menu")
async def back_adm_menu(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.clear()
    await safe_edit(call, "⚙️ <b>Панель администратора:</b>", admin_main_kb())


# ============================ УПРАВЛЕНИЕ ИГРОКОМ ============================

@admin_router.callback_query(F.data == "adm_player_menu")
async def adm_player_menu(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.set_state(AdminStates.adm_find_id)
    await safe_edit(call,
        "👤 <b>Управление игроком</b>\n\n<blockquote>Введите ID или @username игрока:</blockquote>",
        InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="adm_main_menu", style="danger")]])
    )


async def find_user_by_input(text: str):
    text = text.strip()
    if text.startswith("@"):
        uname = text[1:].lower()
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users WHERE LOWER(username) = ?", (uname,)) as cur:
                return await cur.fetchone()
    elif text.isdigit():
        return await get_user(int(text))
    return None


async def build_player_card(target_uid: int):
    user = await get_user(target_uid)
    if not user:
        return None
    ref_count = await get_referrals_count(target_uid)
    text = (
        f"👤 <b>Карточка игрока</b>\n\n<blockquote>"
        f"👤 Ник: <b>{user['username'] or user['user_id']}</b>\n"
        f"🆔 ID: <code>{user['user_id']}</code>\n\n"
        f"💰 Баланс: <b>{user['balance']:.2f} $</b>\n"
        f"📊 Оборот: <b>{user['turnover']:.2f} $</b>\n"
        f"🏆 Ранг: <b>{user['user_rank'] or 'None'}</b>\n"
        f"📥 Депозитов: <b>{user['deposits_count']}</b> (на <b>{user['deposits_sum']:.2f} $</b>)\n"
        f"📤 Выводов: <b>{user['withdrawals_sum']:.2f} $</b>\n"
        f"💎 Кешбэк: <b>{user['cashback_balance']:.2f} $</b>\n"
        f"👥 Рефералов: <b>{ref_count}</b>\n\n"
        f"🚫 Бан: <b>{'ДА' if user['is_banned'] else 'Нет'}</b>\n"
        f"🎮 Игры: <b>{'Запрещены' if user['ban_games'] else 'Разрешены'}</b>\n"
        f"📥 Пополнения: <b>{'Запрещены' if user['ban_deposits'] else 'Разрешены'}</b>\n"
        f"📤 Выводы: <b>{'Запрещены' if user['ban_withdraws'] else 'Разрешены'}</b>\n"
        f"📅 Регистрация: <b>{user['reg_date']}</b>"
        f"</blockquote>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Начислить", callback_data=f"adm_p_add_{target_uid}", style="success"),
            InlineKeyboardButton(text="➖ Списать", callback_data=f"adm_p_sub_{target_uid}", style="danger")
        ],
        [InlineKeyboardButton(text="💰 Установить баланс", callback_data=f"adm_p_set_{target_uid}", style="primary")],
        [
            InlineKeyboardButton(text="🚫 Бан", callback_data=f"adm_p_ban_{target_uid}", style="danger"),
            InlineKeyboardButton(text="🎮 Игры", callback_data=f"adm_p_games_{target_uid}", style="primary")
        ],
        [
            InlineKeyboardButton(text="📥 Депозиты", callback_data=f"adm_p_dep_{target_uid}", style="primary"),
            InlineKeyboardButton(text="📤 Выводы", callback_data=f"adm_p_wd_{target_uid}", style="primary")
        ],
        [
            InlineKeyboardButton(text="🏆 Ранг Bronze", callback_data=f"adm_p_rankB_{target_uid}", style="primary"),
            InlineKeyboardButton(text="🏆 Silver", callback_data=f"adm_p_rankS_{target_uid}", style="primary"),
            InlineKeyboardButton(text="🏆 Gold", callback_data=f"adm_p_rankG_{target_uid}", style="primary")
        ],
        [InlineKeyboardButton(text="♻️ Сбросить оборот", callback_data=f"adm_p_reset_to_{target_uid}", style="danger")],
        [InlineKeyboardButton(text="💬 Сообщение игроку", callback_data=f"adm_p_msg_{target_uid}", style="primary")],
        [InlineKeyboardButton(text="📜 История транзакций", callback_data=f"adm_p_tx_{target_uid}", style="primary")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="adm_player_menu", style="danger")]
    ])
    return text, kb


@admin_router.message(AdminStates.adm_find_id)
async def adm_process_find(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    user = await find_user_by_input(message.text)
    if not user:
        return await message.reply("❌ Игрок не найден. Попробуйте ещё раз:")
    await state.clear()
    text, kb = await build_player_card(user["user_id"])
    await message.reply(text, reply_markup=kb, parse_mode="HTML")


@admin_router.callback_query(F.data.startswith("adm_p_add_"))
async def adm_p_add(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    target_uid = int(call.data.split("_")[3])
    await state.update_data(target_uid=target_uid)
    await state.set_state(AdminStates.adm_add_balance)
    await safe_edit(call,
        f"➕ <b>Начислить баланс игроку</b>\n\n<blockquote>ID: <code>{target_uid}</code>\n\nВведите сумму в $:</blockquote>",
        InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data=f"adm_p_back_{target_uid}", style="danger")]])
    )


@admin_router.message(AdminStates.adm_add_balance)
async def adm_p_add_value(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    target_uid = data["target_uid"]
    try:
        amount = float(message.text.replace(",", ".").replace("$", "").strip())
        if amount <= 0:
            return await message.reply("❌ Сумма должна быть больше 0:")
    except ValueError:
        return await message.reply("❌ Введите число:")
    await admin_user_action(target_uid, "add_balance", amount)
    await state.clear()
    text, kb = await build_player_card(target_uid)
    await message.reply(f"✅ Начислено +{amount:.2f} $ игроку <code>{target_uid}</code>", parse_mode="HTML")
    await message.reply(text, reply_markup=kb, parse_mode="HTML")
    await log_event(bot, "Админ: Начисление баланса", message.from_user,
                    f"Игроку <code>{target_uid}</code> начислено +{amount:.2f} $")


@admin_router.callback_query(F.data.startswith("adm_p_sub_"))
async def adm_p_sub(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    target_uid = int(call.data.split("_")[3])
    await state.update_data(target_uid=target_uid)
    await state.set_state(AdminStates.adm_sub_balance)
    await safe_edit(call,
        f"➖ <b>Списать баланс игроку</b>\n\n<blockquote>ID: <code>{target_uid}</code>\n\nВведите сумму в $:</blockquote>",
        InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data=f"adm_p_back_{target_uid}", style="danger")]])
    )


@admin_router.message(AdminStates.adm_sub_balance)
async def adm_p_sub_value(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    target_uid = data["target_uid"]
    try:
        amount = float(message.text.replace(",", ".").replace("$", "").strip())
        if amount <= 0:
            return await message.reply("❌ Сумма должна быть больше 0:")
    except ValueError:
        return await message.reply("❌ Введите число:")
    await admin_user_action(target_uid, "sub_balance", amount)
    await state.clear()
    text, kb = await build_player_card(target_uid)
    await message.reply(f"✅ Списано -{amount:.2f} $ у игрока <code>{target_uid}</code>", parse_mode="HTML")
    await message.reply(text, reply_markup=kb, parse_mode="HTML")
    await log_event(bot, "Админ: Списание баланса", message.from_user,
                    f"Игроку <code>{target_uid}</code> списано -{amount:.2f} $")


@admin_router.callback_query(F.data.startswith("adm_p_set_"))
async def adm_p_set(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    target_uid = int(call.data.split("_")[3])
    await state.update_data(target_uid=target_uid)
    await state.set_state(AdminStates.adm_set_balance)
    await safe_edit(call,
        f"💰 <b>Установить баланс</b>\n\n<blockquote>ID: <code>{target_uid}</code>\n\nВведите новый баланс в $:</blockquote>",
        InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data=f"adm_p_back_{target_uid}", style="danger")]])
    )


@admin_router.message(AdminStates.adm_set_balance)
async def adm_p_set_value(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    target_uid = data["target_uid"]
    try:
        amount = float(message.text.replace(",", ".").replace("$", "").strip())
        if amount < 0:
            return await message.reply("❌ Баланс не может быть отрицательным:")
    except ValueError:
        return await message.reply("❌ Введите число:")
    await admin_user_action(target_uid, "set_balance", amount)
    await state.clear()
    text, kb = await build_player_card(target_uid)
    await message.reply(f"✅ Баланс игрока <code>{target_uid}</code> = {amount:.2f} $", parse_mode="HTML")
    await message.reply(text, reply_markup=kb, parse_mode="HTML")
    await log_event(bot, "Админ: Установка баланса", message.from_user,
                    f"Игроку <code>{target_uid}</code> установлен баланс {amount:.2f} $")


@admin_router.callback_query(F.data.startswith("adm_p_ban_"))
async def adm_p_ban(call: CallbackQuery, bot: Bot):
    if not is_admin(call.from_user.id):
        return
    target_uid = int(call.data.split("_")[3])
    await admin_user_action(target_uid, "toggle_ban")
    user = await get_user(target_uid)
    status = "ЗАБАНЕН" if user["is_banned"] else "разбанен"
    await call.answer(f"✅ Игрок {status}", show_alert=True)
    text, kb = await build_player_card(target_uid)
    await safe_edit(call, text, kb)
    await log_event(bot, "Админ: Бан игрока", call.from_user,
                    f"Игрок <code>{target_uid}</code> — {status}")


@admin_router.callback_query(F.data.startswith("adm_p_games_"))
async def adm_p_games(call: CallbackQuery, bot: Bot):
    if not is_admin(call.from_user.id):
        return
    target_uid = int(call.data.split("_")[3])
    await admin_user_action(target_uid, "toggle_games")
    user = await get_user(target_uid)
    status = "заблокированы" if user["ban_games"] else "разрешены"
    await call.answer(f"✅ Игры {status}", show_alert=True)
    text, kb = await build_player_card(target_uid)
    await safe_edit(call, text, kb)
    await log_event(bot, "Админ: Блокировка игр", call.from_user,
                    f"Игроку <code>{target_uid}</code> игры {status}")


@admin_router.callback_query(F.data.startswith("adm_p_dep_"))
async def adm_p_dep(call: CallbackQuery, bot: Bot):
    if not is_admin(call.from_user.id):
        return
    target_uid = int(call.data.split("_")[3])
    await admin_user_action(target_uid, "toggle_deposits")
    user = await get_user(target_uid)
    status = "заблокированы" if user["ban_deposits"] else "разрешены"
    await call.answer(f"✅ Пополнения {status}", show_alert=True)
    text, kb = await build_player_card(target_uid)
    await safe_edit(call, text, kb)


@admin_router.callback_query(F.data.startswith("adm_p_wd_"))
async def adm_p_wd(call: CallbackQuery, bot: Bot):
    if not is_admin(call.from_user.id):
        return
    target_uid = int(call.data.split("_")[3])
    await admin_user_action(target_uid, "toggle_withdraws")
    user = await get_user(target_uid)
    status = "заблокированы" if user["ban_withdraws"] else "разрешены"
    await call.answer(f"✅ Выводы {status}", show_alert=True)
    text, kb = await build_player_card(target_uid)
    await safe_edit(call, text, kb)


@admin_router.callback_query(F.data.startswith("adm_p_rankB_"))
async def adm_p_rank_bronze(call: CallbackQuery, bot: Bot):
    if not is_admin(call.from_user.id):
        return
    target_uid = int(call.data.split("_")[3])
    await admin_user_action(target_uid, "set_rank", "Bronze")
    await call.answer("✅ Ранг: Bronze", show_alert=True)
    text, kb = await build_player_card(target_uid)
    await safe_edit(call, text, kb)


@admin_router.callback_query(F.data.startswith("adm_p_rankS_"))
async def adm_p_rank_silver(call: CallbackQuery, bot: Bot):
    if not is_admin(call.from_user.id):
        return
    target_uid = int(call.data.split("_")[3])
    await admin_user_action(target_uid, "set_rank", "Silver")
    await call.answer("✅ Ранг: Silver", show_alert=True)
    text, kb = await build_player_card(target_uid)
    await safe_edit(call, text, kb)


@admin_router.callback_query(F.data.startswith("adm_p_rankG_"))
async def adm_p_rank_gold(call: CallbackQuery, bot: Bot):
    if not is_admin(call.from_user.id):
        return
    target_uid = int(call.data.split("_")[3])
    await admin_user_action(target_uid, "set_rank", "Gold")
    await call.answer("✅ Ранг: Gold", show_alert=True)
    text, kb = await build_player_card(target_uid)
    await safe_edit(call, text, kb)


@admin_router.callback_query(F.data.startswith("adm_p_reset_to_"))
async def adm_p_reset_to(call: CallbackQuery, bot: Bot):
    if not is_admin(call.from_user.id):
        return
    target_uid = int(call.data.split("_")[4])
    await admin_user_action(target_uid, "reset_turnover")
    await call.answer("✅ Оборот сброшен", show_alert=True)
    text, kb = await build_player_card(target_uid)
    await safe_edit(call, text, kb)


@admin_router.callback_query(F.data.startswith("adm_p_msg_"))
async def adm_p_msg(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    target_uid = int(call.data.split("_")[3])
    await state.update_data(target_uid=target_uid)
    await state.set_state(AdminStates.adm_msg_to_user)
    await safe_edit(call,
        f"💬 <b>Сообщение игроку</b>\n\n<blockquote>ID: <code>{target_uid}</code>\n\nВведите текст:</blockquote>",
        InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data=f"adm_p_back_{target_uid}", style="danger")]])
    )


@admin_router.message(AdminStates.adm_msg_to_user)
async def adm_p_msg_send(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    target_uid = data["target_uid"]
    try:
        await bot.send_message(
            target_uid,
            f"📩 <b>Сообщение от администратора:</b>\n\n"
            f"<blockquote>{message.text}</blockquote>",
            parse_mode="HTML"
        )
        await message.reply("✅ Сообщение отправлено!")
    except Exception as e:
        await message.reply(f"❌ Не удалось отправить: {e}")
    await state.clear()


@admin_router.callback_query(F.data.startswith("adm_p_tx_"))
async def adm_p_tx(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    target_uid = int(call.data.split("_")[3])
    rows = await get_transactions(target_uid, limit=15)
    if not rows:
        return await call.answer("История транзакций пуста.", show_alert=True)
    lines = [f"📜 <b>Транзакции игрока</b> <code>{target_uid}</code>\n<blockquote>"]
    for r in rows:
        emoji = "🟢" if r["status"] == "success" else "🔴"
        lines.append(f"{emoji} {r['type'].upper()}: {r['amount']:.2f}$ ({r['gateway']}) | {r['created_at'].split()[0]}")
    lines.append("</blockquote>")
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data=f"adm_p_back_{target_uid}", style="danger")]])
    await safe_edit(call, "\n".join(lines), kb)


@admin_router.callback_query(F.data.startswith("adm_p_back_"))
async def adm_p_back(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    target_uid = int(call.data.split("_")[3])
    await state.clear()
    text, kb = await build_player_card(target_uid)
    await safe_edit(call, text, kb)


# ============================ ОСТАЛЬНЫЕ ФУНКЦИИ ============================

@admin_router.callback_query(F.data == "adm_gateways_menu")
async def adm_gateways_menu(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    cb_status = await get_setting("gateway_cryptobot", "1")
    cb_btn_text = "🟢 CryptoBot: Вкл" if cb_status == "1" else "🔴 CryptoBot: Выкл"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=cb_btn_text, callback_data="adm_toggle_gw_cryptobot", style="success" if cb_status == "1" else "danger")],
        [InlineKeyboardButton(text="⬅️ В панель", callback_data="adm_main_menu", style="danger")]
    ])
    await safe_edit(call,
        "💳 <b>Управление шлюзами пополнений:</b>\n\n<blockquote>Включение/выключение CryptoBot.</blockquote>",
        kb
    )


@admin_router.callback_query(F.data.startswith("adm_toggle_gw_"))
async def adm_toggle_gateway(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    gw = call.data.replace("adm_toggle_gw_", "")
    key = f"gateway_{gw}"
    current = await get_setting(key, "1")
    new_val = "0" if current == "1" else "1"
    await set_setting(key, new_val)
    await call.answer(f"Шлюз {gw}: {new_val}", show_alert=True)
    await adm_gateways_menu(call)


@admin_router.callback_query(F.data == "adm_create_promo")
async def start_create_promo(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.set_state(AdminStates.waiting_for_promo_code)
    await safe_edit(call, "🎁 <b>Введите промокод:</b>",
                    InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data="adm_main_menu", style="danger")]]))


@admin_router.message(AdminStates.waiting_for_promo_code)
async def process_promo_name(message: Message, state: FSMContext):
    await state.update_data(promo_code=message.text.strip().upper())
    await state.set_state(AdminStates.waiting_for_promo_reward)
    await message.reply("💵 Сумма бонуса:")


@admin_router.message(AdminStates.waiting_for_promo_reward)
async def process_promo_rew(message: Message, state: FSMContext):
    try:
        rew = float(message.text.replace(",", "."))
    except ValueError:
        return await message.reply("❌ Число:")
    data = await state.get_data()
    await create_promo_code(data["promo_code"], rew, 100)
    await state.clear()
    await message.reply("✅ Промокод создан!", reply_markup=admin_main_kb())


@admin_router.callback_query(F.data == "adm_stats")
async def show_stats(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*), SUM(balance) FROM users") as cur:
            row = await cur.fetchone()
        async with db.execute("SELECT COUNT(*) FROM users WHERE is_banned = 1") as cur:
            banned = await cur.fetchone()
    total = row[1] if row[1] else 0.0
    text = (
        f"📊 <b>Статистика</b>\n\n<blockquote>"
        f"👥 Юзеров: <b>{row[0]}</b>\n"
        f"💰 Общий баланс: <b>{total:.2f} $</b>\n"
        f"🚫 Забанено: <b>{banned[0]}</b>"
        f"</blockquote>"
    )
    await safe_edit(call, text,
                    InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Назад", callback_data="adm_main_menu", style="danger")]]))


@admin_router.callback_query(F.data == "adm_reset_top")
async def reset_top(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    await reset_top_statistics()
    await call.answer("✅ Топы сброшены!", show_alert=True)
    await safe_edit(call, "⚙️ Меню администратора", admin_main_kb())


@admin_router.callback_query(F.data == "adm_broadcast_start")
async def start_bc(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.set_state(AdminStates.waiting_for_broadcast_text)
    await safe_edit(call, "📢 <b>Введите текст рассылки:</b>",
                    InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data="adm_main_menu", style="danger")]]))


@admin_router.message(AdminStates.waiting_for_broadcast_text)
async def proc_bc(message: Message, state: FSMContext):
    uids = await get_all_user_ids()
    ok_count = 0
    for uid in uids:
        try:
            await message.bot.send_message(uid, message.text, parse_mode="HTML")
            ok_count += 1
            await asyncio.sleep(0.04)
        except Exception:
            pass
    await state.clear()
    await message.reply(f"✅ Рассылка завершена! Доставлено: {ok_count}/{len(uids)}", reply_markup=admin_main_kb())