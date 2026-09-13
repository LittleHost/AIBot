# handlers_games.py
import asyncio
import secrets
import hashlib
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from database import (
    get_user, update_balance, add_turnover, record_game,
    set_user_setting, db_save_session, db_get_session, db_delete_session,
    db_cancel_active_session
)
from config import EMOJI, ICON_IDS
from utils import safe_edit, log_event

games_router = Router()

DICE_BETS = [0.05, 0.1, 0.5, 1.0, 2.0, 5.0]

USER_LOCKS = {}


def get_lock(uid: int) -> asyncio.Lock:
    if uid not in USER_LOCKS:
        USER_LOCKS[uid] = asyncio.Lock()
    return USER_LOCKS[uid]


def create_seed():
    salt = secrets.token_hex(16)
    salt_hash = hashlib.sha256(salt.encode()).hexdigest()
    return salt, salt_hash


def calc_mines_mult(mines: int, step: int) -> float:
    total, safe = 25, 25 - mines
    if step <= 0 or step > safe:
        return 1.0
    prob = 1.0
    for i in range(step):
        prob *= (safe - i) / (total - i)
    return round(1.0 / prob, 2)


TOWER_EXACT_RATES = {1: [1.10, 1.30, 1.50, 1.90, 2.00, 2.40, 2.80, 3.60, 4.00, 5.60]}


def calc_tower_mult(traps: int, floor: int) -> float:
    if floor <= 0:
        return 1.0
    if traps == 1 and floor <= len(TOWER_EXACT_RATES[1]):
        return TOWER_EXACT_RATES[1][floor - 1]
    prob = ((5.0 - traps) / 5.0) ** floor
    return round(1.0 / prob, 2) if prob > 0 else 999999.0


# ==================== КОСТИ (DICE) ====================

def dice_menu_kb(cur_bet: float, in_chat: bool = False) -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="🎯 На число (x6.0)", callback_data="dice_m_exact", style="primary")],
        [
            InlineKeyboardButton(text="⚖️ Чёт / Нечет (x1.9)", callback_data="dice_m_parity", style="primary"),
            InlineKeyboardButton(text="📊 Больше / Меньше (x1.9)", callback_data="dice_m_hl", style="primary")
        ],
        [
            InlineKeyboardButton(text="🎲 7+ / 7- / 7=", callback_data="dice_m_seven", style="primary"),
            InlineKeyboardButton(text="18+ / 18-", callback_data="dice_m_mult18", style="danger", icon_custom_emoji_id=ICON_IDS["fire"])
        ],
        [InlineKeyboardButton(text=f"Ставка: {cur_bet}$", callback_data="dice_change_bet", style="success", icon_custom_emoji_id=ICON_IDS["cash"])]
    ]
    if not in_chat:
        kb.append([InlineKeyboardButton(text="Назад", callback_data="open_games", style="danger", icon_custom_emoji_id=ICON_IDS["cross"])])
    return InlineKeyboardMarkup(inline_keyboard=kb)


@games_router.callback_query(F.data == "game_dice")
async def open_dice_menu(call: CallbackQuery):
    user = await get_user(call.from_user.id)
    is_group = call.message.chat.type in ["group", "supergroup"]
    text = (
        f"🎲 <b>Кости (Native Dice)</b>\n\n<blockquote>"
        f"Баланс: <b>{user['balance']:.2f}</b> {EMOJI['cash']}\n"
        f"Ставка: <b>{user['selected_bet']:.2f}</b> {EMOJI['cash']}\n\n"
        f"Все броски — официальный генератор Telegram!</blockquote>"
    )
    await safe_edit(call, text, dice_menu_kb(user['selected_bet'], in_chat=is_group))


@games_router.callback_query(F.data == "dice_change_bet")
async def change_bet_call(call: CallbackQuery):
    user = await get_user(call.from_user.id)
    kb = []
    row = []
    for b in DICE_BETS:
        mark = "🔘" if b == user["selected_bet"] else "▫️"
        row.append(InlineKeyboardButton(text=f"{mark} {b}$", callback_data=f"set_bet_{b}", style="primary"))
        if len(row) == 3:
            kb.append(row)
            row = []
    if row:
        kb.append(row)
    kb.append([InlineKeyboardButton(text="Назад", callback_data="game_dice", style="danger", icon_custom_emoji_id=ICON_IDS["cross"])])
    await safe_edit(call, f"{EMOJI['cash']} <b>Выберите ставку:</b>", InlineKeyboardMarkup(inline_keyboard=kb))


@games_router.callback_query(F.data.startswith("set_bet_"))
async def set_bet_val(call: CallbackQuery):
    b = float(call.data.split("_")[2])
    await set_user_setting(call.from_user.id, "selected_bet", b)
    await call.answer(f"Ставка: {b}$")
    await open_dice_menu(call)


async def run_dice_game(call: CallbackQuery, mode_name, count_dices, check_fn):
    uid = call.from_user.id
    user = await get_user(uid)
    bet = user["selected_bet"]
    if user["ban_games"]:
        return await call.answer("❌ Игры заблокированы.", show_alert=True)
    if user["balance"] < bet:
        return await call.answer("❌ Недостаточно средств!", show_alert=True)
    await update_balance(uid, -bet)
    await add_turnover(uid, bet)
    try:
        await call.message.delete()
    except Exception:
        pass
    is_group = call.message.chat.type in ["group", "supergroup"]
    c_id = call.message.chat.id if is_group else 0
    c_title = call.message.chat.title if is_group else ""
    dices = []
    for _ in range(count_dices):
        msg = await call.message.answer_dice(emoji="🎲")
        dices.append(msg.dice.value)
    await asyncio.sleep(3.5 if count_dices == 1 else 4.0)
    win, rate, desc = check_fn(dices)
    if win:
        payout = round(bet * rate, 2)
        await update_balance(uid, payout)
        await record_game(uid, f"Кости: {mode_name}", bet, payout, True, chat_id=c_id, chat_title=c_title)
        await call.message.answer(
            f"{EMOJI['trophy']} <b>Победа! {desc}</b>\n\n"
            f"<blockquote>Выигрыш: <b>+{payout:.2f}</b> {EMOJI['cash']} (x{rate})</blockquote>",
            reply_markup=dice_menu_kb(bet, in_chat=is_group), parse_mode="HTML"
        )
    else:
        await record_game(uid, f"Кости: {mode_name}", bet, 0.0, False, chat_id=c_id, chat_title=c_title)
        await call.message.answer(
            f"{EMOJI['cross']} <b>Проигрыш! {desc}</b>\n\n"
            f"<blockquote>Ставка <b>{bet:.2f}</b> {EMOJI['cash']} сгорела.</blockquote>",
            reply_markup=dice_menu_kb(bet, in_chat=is_group), parse_mode="HTML"
        )


@games_router.callback_query(F.data == "dice_m_exact")
async def choose_exact(call: CallbackQuery):
    kb = [
        [InlineKeyboardButton(text=f"🎲 {i}", callback_data=f"dice_exact_{i}", style="primary") for i in range(1, 4)],
        [InlineKeyboardButton(text=f"🎲 {i}", callback_data=f"dice_exact_{i}", style="primary") for i in range(4, 7)],
        [InlineKeyboardButton(text="Назад", callback_data="game_dice", style="danger", icon_custom_emoji_id=ICON_IDS["cross"])]
    ]
    await safe_edit(call, "🎯 <b>Выберите число (x6.0):</b>", InlineKeyboardMarkup(inline_keyboard=kb))


@games_router.callback_query(F.data.startswith("dice_exact_"))
async def run_exact_action(call: CallbackQuery):
    target = int(call.data.split("_")[2])
    await run_dice_game(call, "Точное", 1,
                        lambda d: (d[0] == target, 6.0, f"Выпало {d[0]} (на {target})"))


@games_router.callback_query(F.data == "dice_m_parity")
async def choose_parity(call: CallbackQuery):
    kb = [
        [
            InlineKeyboardButton(text="Чёт (x1.9)", callback_data="dice_par_even", style="primary"),
            InlineKeyboardButton(text="Нечет (x1.9)", callback_data="dice_par_odd", style="primary")
        ],
        [InlineKeyboardButton(text="Назад", callback_data="game_dice", style="danger", icon_custom_emoji_id=ICON_IDS["cross"])]
    ]
    await safe_edit(call, "⚖️ <b>Чёт или Нечет:</b>", InlineKeyboardMarkup(inline_keyboard=kb))


@games_router.callback_query(F.data.startswith("dice_par_"))
async def run_parity_action(call: CallbackQuery):
    t = call.data.split("_")[2]
    await run_dice_game(call, "Чет/Нечет", 1,
                        lambda d: (((d[0] % 2 == 0) if t == "even" else (d[0] % 2 != 0)), 1.9, f"Выпало {d[0]}"))


@games_router.callback_query(F.data == "dice_m_hl")
async def choose_hl(call: CallbackQuery):
    kb = [
        [
            InlineKeyboardButton(text="1-3 (x1.9)", callback_data="dice_hl_l", style="primary"),
            InlineKeyboardButton(text="4-6 (x1.9)", callback_data="dice_hl_h", style="primary")
        ],
        [InlineKeyboardButton(text="Назад", callback_data="game_dice", style="danger", icon_custom_emoji_id=ICON_IDS["cross"])]
    ]
    await safe_edit(call, "📊 <b>Больше/Меньше:</b>", InlineKeyboardMarkup(inline_keyboard=kb))


@games_router.callback_query(F.data.startswith("dice_hl_"))
async def run_hl_action(call: CallbackQuery):
    t = call.data.split("_")[2]
    await run_dice_game(call, "Больше/Меньше", 1,
                        lambda d: (((d[0] <= 3) if t == "l" else (d[0] >= 4)), 1.9, f"Выпало {d[0]}"))


@games_router.callback_query(F.data == "dice_m_seven")
async def choose_seven(call: CallbackQuery):
    kb = [
        [
            InlineKeyboardButton(text="7- (x2.7)", callback_data="dice_sev_l", style="primary"),
            InlineKeyboardButton(text="7= (x6.0)", callback_data="dice_sev_e", style="success"),
            InlineKeyboardButton(text="7+ (x2.7)", callback_data="dice_sev_h", style="primary")
        ],
        [InlineKeyboardButton(text="Назад", callback_data="game_dice", style="danger", icon_custom_emoji_id=ICON_IDS["cross"])]
    ]
    await safe_edit(call, "🎲 <b>Сумма двух кубиков:</b>", InlineKeyboardMarkup(inline_keyboard=kb))


@games_router.callback_query(F.data.startswith("dice_sev_"))
async def run_seven_action(call: CallbackQuery):
    t = call.data.split("_")[2]
    def eval_7(d):
        s = d[0] + d[1]
        desc = f"Выпало: {d[0]} + {d[1]} = {s}"
        if t == "l" and s < 7: return True, 2.7, desc
        if t == "h" and s > 7: return True, 2.7, desc
        if t == "e" and s == 7: return True, 6.0, desc
        return False, 0.0, desc
    await run_dice_game(call, "7-значения", 2, eval_7)


@games_router.callback_query(F.data == "dice_m_mult18")
async def choose_m18(call: CallbackQuery):
    kb = [
        [
            InlineKeyboardButton(text="18- (x1.2)", callback_data="dice_18_l", style="primary"),
            InlineKeyboardButton(text="18+ (x4.0)", callback_data="dice_18_h", style="danger", icon_custom_emoji_id=ICON_IDS["fire"])
        ],
        [InlineKeyboardButton(text="Назад", callback_data="game_dice", style="danger", icon_custom_emoji_id=ICON_IDS["cross"])]
    ]
    await safe_edit(call, f"{EMOJI['fire']} <b>Произведение кубиков:</b>", InlineKeyboardMarkup(inline_keyboard=kb))


@games_router.callback_query(F.data.startswith("dice_18_"))
async def run_m18_action(call: CallbackQuery):
    t = call.data.split("_")[2]
    def eval_18(d):
        p = d[0] * d[1]
        desc = f"Выпало: {d[0]} * {d[1]} = {p}"
        if t == "l" and p < 18: return True, 1.2, desc
        if t == "h" and p >= 18: return True, 4.0, desc
        return False, 0.0, desc
    await run_dice_game(call, "18-умножение", 2, eval_18)


# ==================== МИНЫ (MINES) ====================

@games_router.message(Command("game_off"))
async def cmd_cancel_game(message: Message):
    uid = message.from_user.id
    async with get_lock(uid):
        deleted = await db_cancel_active_session(uid)
    if deleted:
        await message.reply("🛑 <b>Игра отменена!</b>\n<blockquote>Сессия очищена.</blockquote>", parse_mode="HTML")
    else:
        await message.reply("ℹ️ Нет активных игр.")


@games_router.callback_query(F.data == "game_provably_fair")
async def show_provably_fair_info(call: CallbackQuery):
    sess = await db_get_session(call.from_user.id)
    if not sess:
        return await call.answer("❌ Игра завершена.", show_alert=True)
    data = sess["data"]
    info_text = f"🛡️ Provably Fair\n\nSHA-256 Hash:\n{data['hash']}\n\nСоль скрыта до конца игры."
    await call.answer(info_text, show_alert=True)


@games_router.callback_query(F.data == "game_mines")
async def open_mines_menu(call: CallbackQuery):
    user = await get_user(call.from_user.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Начать играть", callback_data="mines_play_round", style="success", icon_custom_emoji_id=ICON_IDS["rocket"])],
        [
            InlineKeyboardButton(text=f"💣 Мин: {user['selected_mines']}", callback_data="change_mines_cnt", style="primary", icon_custom_emoji_id=ICON_IDS["mine"]),
            InlineKeyboardButton(text=f"💵 Ставка: {user['selected_bet']:.2f} $", callback_data="dice_change_bet", style="success", icon_custom_emoji_id=ICON_IDS["cash"])
        ],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="open_games", style="danger", icon_custom_emoji_id=ICON_IDS["cross"])]
    ])
    text = (
        f"{EMOJI['mine']} <b>Мины (Mines 5x5)</b>\n\n<blockquote>"
        f"{EMOJI['cash']} Баланс: <b>{user['balance']:.2f} $</b>\n"
        f"{EMOJI['star']} Ставка: <b>{user['selected_bet']:.2f} $</b>\n"
        f"{EMOJI['mine']} Мин: <b>{user['selected_mines']}</b>\n\n"
        f"{EMOJI['shield']} <i>Provably Fair SHA-256</i></blockquote>"
    )
    await safe_edit(call, text, kb)


@games_router.callback_query(F.data == "change_mines_cnt")
async def select_mines_cnt_call(call: CallbackQuery):
    presets = [2, 3, 5, 10, 15, 20, 24]
    kb = []
    row = []
    for p in presets:
        row.append(InlineKeyboardButton(text=f"💣 {p}", callback_data=f"set_mines_{p}", style="primary"))
        if len(row) == 3:
            kb.append(row)
            row = []
    if row:
        kb.append(row)
    kb.append([InlineKeyboardButton(text="Назад", callback_data="game_mines", style="danger", icon_custom_emoji_id=ICON_IDS["cross"])])
    await safe_edit(call, "⚙️ <b>Количество мин:</b>", InlineKeyboardMarkup(inline_keyboard=kb))


@games_router.callback_query(F.data.startswith("set_mines_"))
async def set_mines_val(call: CallbackQuery):
    cnt = int(call.data.split("_")[2])
    await set_user_setting(call.from_user.id, "selected_mines", cnt)
    await call.answer(f"Установлено: {cnt} мин")
    await open_mines_menu(call)


def build_mines_kb(grid, active, win_amt) -> InlineKeyboardMarkup:
    kb = []
    for r in range(5):
        row = []
        for c in range(5):
            idx = r * 5 + c
            v = grid[idx]
            text = "▫️" if v is None else ("💎" if v == 0 else "💣")
            cb = f"m_clk_{idx}" if (active and v is None) else "none"
            row.append(InlineKeyboardButton(text=text, callback_data=cb))
        kb.append(row)
    if active:
        control_row = []
        if win_amt > 0:
            control_row.append(InlineKeyboardButton(
                text=f"Забрать {win_amt:.2f} $", callback_data="m_cashout", style="success", icon_custom_emoji_id=ICON_IDS["cash"]
            ))
        control_row.append(InlineKeyboardButton(text="Честность", callback_data="game_provably_fair", style="primary", icon_custom_emoji_id=ICON_IDS["shield"]))
        kb.append(control_row)
    else:
        kb.append([
            InlineKeyboardButton(text="🔄 Повторить", callback_data="mines_play_round", style="success", icon_custom_emoji_id=ICON_IDS["rocket"]),
            InlineKeyboardButton(text="💵 Меню", callback_data="game_mines", style="primary", icon_custom_emoji_id=ICON_IDS["cash"])
        ])
        kb.append([InlineKeyboardButton(text="В меню", callback_data="open_games", style="danger", icon_custom_emoji_id=ICON_IDS["cross"])])
    return InlineKeyboardMarkup(inline_keyboard=kb)


@games_router.callback_query(F.data == "mines_play_round")
async def start_mines_action(call: CallbackQuery):
    uid = call.from_user.id
    async with get_lock(uid):
        sess = await db_get_session(uid)
        if sess:
            return await call.answer("❌ Завершите текущую игру /game_off", show_alert=True)
        user = await get_user(uid)
        bet = user["selected_bet"]
        mines_count = user["selected_mines"]
        if user["ban_games"]:
            return await call.answer("❌ Игры заблокированы.", show_alert=True)
        if user["balance"] < bet:
            return await call.answer("❌ Недостаточно средств!", show_alert=True)
        await update_balance(uid, -bet)
        await add_turnover(uid, bet)
        field = [1] * mines_count + [0] * (25 - mines_count)
        rng = secrets.SystemRandom()
        rng.shuffle(field)
        salt, s_hash = create_seed()
        is_group = call.message.chat.type in ["group", "supergroup"]
        data = {
            "field": field, "grid": [None] * 25, "mines": mines_count, "bet": bet, "step": 0,
            "salt": salt, "hash": s_hash,
            "chat_id": call.message.chat.id if is_group else 0,
            "chat_title": call.message.chat.title if is_group else ""
        }
        await db_save_session(uid, "mines", data)
    text = (
        f"{EMOJI['mine']} <b>Мины запущены!</b>\n\n"
        f"<blockquote>Мин: <b>{mines_count}</b> | Ставка: <b>{bet:.2f} $</b>\n"
        f"SHA-256:\n<code>{s_hash}</code></blockquote>"
    )
    await safe_edit(call, text, build_mines_kb(data["grid"], True, 0))


@games_router.callback_query(F.data.startswith("m_clk_"))
async def click_mine_cell(call: CallbackQuery):
    uid = call.from_user.id
    async with get_lock(uid):
        session = await db_get_session(uid)
        if not session or session["game_type"] != "mines":
            return await call.answer("Игра не найдена. /game_off")
        data = session["data"]
        idx = int(call.data.split("_")[2])
        if data["grid"][idx] is not None:
            return await call.answer()
        if data["field"][idx] == 1:
            await db_delete_session(uid)
            await record_game(uid, "Мины", data["bet"], 0.0, False,
                              chat_id=data.get("chat_id", 0), chat_title=data.get("chat_title", ""))
            text = (
                f"💥 <b>БАБАХ! Мина!</b>\n\n"
                f"<blockquote>Потеряно: <b>{data['bet']:.2f}</b> {EMOJI['cash']}\n\n"
                f"🛡️ Hash: <code>{data['hash']}</code>\n"
                f"Соль: <code>{data['salt']}</code></blockquote>"
            )
            return await safe_edit(call, text, build_mines_kb(data["field"], False, 0))
        data["step"] += 1
        data["grid"][idx] = 0
        coef = calc_mines_mult(data["mines"], data["step"])
        win_amt = round(data["bet"] * coef, 2)
        if data["step"] == (25 - data["mines"]):
            await db_delete_session(uid)
            await update_balance(uid, win_amt)
            await record_game(uid, "Мины", data["bet"], win_amt, True,
                              chat_id=data.get("chat_id", 0), chat_title=data.get("chat_title", ""))
            text = (
                f"{EMOJI['trophy']} <b>ПОЛЕ ЗАЧИЩЕНО!</b>\n\n"
                f"<blockquote>Множитель: <b>x{coef}</b> | Выигрыш: <b>+{win_amt:.2f} $</b>\n\n"
                f"Hash: <code>{data['hash']}</code>\nСоль: <code>{data['salt']}</code></blockquote>"
            )
            return await safe_edit(call, text, build_mines_kb(data["grid"], False, 0))
        await db_save_session(uid, "mines", data)
    text = (
        f"{EMOJI['gem']} <b>Алмаз!</b>\n\n"
        f"<blockquote>Шаг: <b>{data['step']}</b> | Множитель: <b>x{coef}</b>\n"
        f"К выводу: <b>{win_amt:.2f} $</b>\n"
        f"Hash: <code>{data['hash'][:20]}...</code></blockquote>"
    )
    await safe_edit(call, text, build_mines_kb(data["grid"], True, win_amt))


@games_router.callback_query(F.data == "m_cashout")
async def mines_cashout_call(call: CallbackQuery):
    uid = call.from_user.id
    async with get_lock(uid):
        session = await db_get_session(uid)
        if not session or session["game_type"] != "mines":
            return await call.answer()
        data = session["data"]
        await db_delete_session(uid)
        coef = calc_mines_mult(data["mines"], data["step"])
        payout = round(data["bet"] * coef, 2)
        await update_balance(uid, payout)
        await record_game(uid, "Мины", data["bet"], payout, True,
                          chat_id=data.get("chat_id", 0), chat_title=data.get("chat_title", ""))
    text = (
        f"{EMOJI['cash']} <b>Забрали!</b>\n\n"
        f"<blockquote>Множитель: <b>x{coef}</b> | Выплата: <b>+{payout:.2f} $</b>\n\n"
        f"Hash: <code>{data['hash']}</code>\nСоль: <code>{data['salt']}</code></blockquote>"
    )
    await safe_edit(call, text, build_mines_kb(data["field"], False, 0))


# ==================== БАШНЯ (TOWER) ====================

@games_router.callback_query(F.data == "game_tower")
async def open_tower_menu(call: CallbackQuery):
    user = await get_user(call.from_user.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Начать подъем", callback_data="tower_play_round", style="success", icon_custom_emoji_id=ICON_IDS["rocket"])],
        [
            InlineKeyboardButton(text=f"🛡️ Ловушек: {user['selected_traps']}", callback_data="change_traps_cnt", style="primary"),
            InlineKeyboardButton(text=f"💵 Ставка: {user['selected_bet']:.2f} $", callback_data="dice_change_bet", style="success", icon_custom_emoji_id=ICON_IDS["cash"])
        ],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="open_games", style="danger", icon_custom_emoji_id=ICON_IDS["cross"])]
    ])
    text = (
        f"{EMOJI['tower']} <b>Башня (5x10)</b>\n\n<blockquote>"
        f"Баланс: <b>{user['balance']:.2f} $</b>\n"
        f"Ставка: <b>{user['selected_bet']:.2f} $</b>\n"
        f"Ловушек: <b>{user['selected_traps']}</b></blockquote>"
    )
    await safe_edit(call, text, kb)


@games_router.callback_query(F.data == "change_traps_cnt")
async def change_traps_call(call: CallbackQuery):
    kb = [
        [InlineKeyboardButton(text="1 ловушка (Легкий)", callback_data="set_traps_1", style="primary")],
        [InlineKeyboardButton(text="2 ловушки (Средний)", callback_data="set_traps_2", style="primary")],
        [InlineKeyboardButton(text="3 ловушки (Сложный)", callback_data="set_traps_3", style="primary")],
        [InlineKeyboardButton(text="4 ловушки (Экстрим)", callback_data="set_traps_4", style="danger", icon_custom_emoji_id=ICON_IDS["fire"])],
        [InlineKeyboardButton(text="Назад", callback_data="game_tower", style="danger", icon_custom_emoji_id=ICON_IDS["cross"])]
    ]
    await safe_edit(call, "⚙️ <b>Сложность:</b>", InlineKeyboardMarkup(inline_keyboard=kb))


@games_router.callback_query(F.data.startswith("set_traps_"))
async def set_traps_val(call: CallbackQuery):
    t = int(call.data.split("_")[2])
    await set_user_setting(call.from_user.id, "selected_traps", t)
    await call.answer(f"Сложность: {t}")
    await open_tower_menu(call)


def build_tower_kb(floor, history, active, win_amt) -> InlineKeyboardMarkup:
    kb = []
    for r in range(9, -1, -1):
        row = []
        if r == floor and active:
            for c in range(5):
                row.append(InlineKeyboardButton(text="❓", callback_data=f"t_clk_{c}", style="primary"))
        elif r < floor or not active:
            row_d = history[r] if r < len(history) else [None] * 5
            for c in range(5):
                v = row_d[c]
                row.append(InlineKeyboardButton(text="⭐" if v == 0 else ("💥" if v == 1 else "▫️"), callback_data="none"))
        else:
            for _ in range(5):
                row.append(InlineKeyboardButton(text="▫️", callback_data="none"))
        kb.append(row)
    if active:
        control_row = []
        if floor > 0 and win_amt > 0:
            control_row.append(InlineKeyboardButton(
                text=f"Забрать {win_amt:.2f} $", callback_data="t_cashout", style="success", icon_custom_emoji_id=ICON_IDS["cash"]
            ))
        control_row.append(InlineKeyboardButton(text="Честность", callback_data="game_provably_fair", style="primary", icon_custom_emoji_id=ICON_IDS["shield"]))
        kb.append(control_row)
    else:
        kb.append([
            InlineKeyboardButton(text="🔄 Повторить", callback_data="tower_play_round", style="success", icon_custom_emoji_id=ICON_IDS["rocket"]),
            InlineKeyboardButton(text="💵 Меню", callback_data="game_tower", style="primary", icon_custom_emoji_id=ICON_IDS["cash"])
        ])
        kb.append([InlineKeyboardButton(text="В меню", callback_data="open_games", style="danger", icon_custom_emoji_id=ICON_IDS["cross"])])
    return InlineKeyboardMarkup(inline_keyboard=kb)


@games_router.callback_query(F.data == "tower_play_round")
async def start_tower_action(call: CallbackQuery):
    uid = call.from_user.id
    async with get_lock(uid):
        sess = await db_get_session(uid)
        if sess:
            return await call.answer("❌ Завершите текущую /game_off", show_alert=True)
        user = await get_user(uid)
        bet = user["selected_bet"]
        traps = user["selected_traps"]
        if user["ban_games"]:
            return await call.answer("❌ Игры заблокированы.", show_alert=True)
        if user["balance"] < bet:
            return await call.answer("❌ Недостаточно средств!", show_alert=True)
        await update_balance(uid, -bet)
        await add_turnover(uid, bet)
        rng = secrets.SystemRandom()
        grid = []
        for _ in range(10):
            row = [1] * traps + [0] * (5 - traps)
            rng.shuffle(row)
            grid.append(row)
        salt, s_hash = create_seed()
        is_group = call.message.chat.type in ["group", "supergroup"]
        data = {
            "grid": grid, "floor": 0, "traps": traps, "bet": bet,
            "salt": salt, "hash": s_hash,
            "chat_id": call.message.chat.id if is_group else 0,
            "chat_title": call.message.chat.title if is_group else ""
        }
        await db_save_session(uid, "tower", data)
    text = (
        f"{EMOJI['tower']} <b>Башня запущена!</b>\n\n"
        f"<blockquote>Ловушек: <b>{traps}</b> | Ставка: <b>{bet:.2f} $</b>\n"
        f"SHA-256:\n<code>{s_hash}</code></blockquote>"
    )
    await safe_edit(call, text, build_tower_kb(0, grid, True, 0))


@games_router.callback_query(F.data.startswith("t_clk_"))
async def click_tower_floor(call: CallbackQuery):
    uid = call.from_user.id
    async with get_lock(uid):
        session = await db_get_session(uid)
        if not session or session["game_type"] != "tower":
            return await call.answer("Игра не найдена. /game_off")
        data = session["data"]
        col = int(call.data.split("_")[2])
        fl = data["floor"]
        if data["grid"][fl][col] == 1:
            await db_delete_session(uid)
            await record_game(uid, "Башня", data["bet"], 0.0, False,
                              chat_id=data.get("chat_id", 0), chat_title=data.get("chat_title", ""))
            text = (
                f"💥 <b>Ловушка на этаже {fl+1}!</b>\n\n"
                f"<blockquote>Потеряно: <b>{data['bet']:.2f}</b> {EMOJI['cash']}\n\n"
                f"Hash: <code>{data['hash']}</code>\nСоль: <code>{data['salt']}</code></blockquote>"
            )
            return await safe_edit(call, text, build_tower_kb(fl, data["grid"], False, 0))
        data["floor"] += 1
        coef = calc_tower_mult(data["traps"], data["floor"])
        cur_win = round(data["bet"] * coef, 2)
        if data["floor"] == 10:
            await db_delete_session(uid)
            await update_balance(uid, cur_win)
            await record_game(uid, "Башня", data["bet"], cur_win, True,
                              chat_id=data.get("chat_id", 0), chat_title=data.get("chat_title", ""))
            text = (
                f"{EMOJI['trophy']} <b>ВЕРШИНА ПОКОРЕНА!</b>\n\n"
                f"<blockquote>Множитель: <b>x{coef}</b> | Выигрыш: <b>+{cur_win:.2f} $</b>\n\n"
                f"Hash: <code>{data['hash']}</code>\nСоль: <code>{data['salt']}</code></blockquote>"
            )
            return await safe_edit(call, text, build_tower_kb(10, data["grid"], False, 0))
        await db_save_session(uid, "tower", data)
    text = (
        f"{EMOJI['tower']} <b>Этаж {data['floor']}!</b>\n\n"
        f"<blockquote>Множитель: <b>x{coef}</b> | Банк: <b>{cur_win:.2f} $</b>\n"
        f"Hash: <code>{data['hash'][:20]}...</code></blockquote>"
    )
    await safe_edit(call, text, build_tower_kb(data["floor"], data["grid"], True, cur_win))


@games_router.callback_query(F.data == "t_cashout")
async def tower_cashout_call(call: CallbackQuery):
    uid = call.from_user.id
    async with get_lock(uid):
        session = await db_get_session(uid)
        if not session or session["game_type"] != "tower":
            return await call.answer()
        data = session["data"]
        await db_delete_session(uid)
        coef = calc_tower_mult(data["traps"], data["floor"])
        win = round(data["bet"] * coef, 2)
        await update_balance(uid, win)
        await record_game(uid, "Башня", data["bet"], win, True,
                          chat_id=data.get("chat_id", 0), chat_title=data.get("chat_title", ""))
    text = (
        f"{EMOJI['cash']} <b>Забрали из башни!</b>\n\n"
        f"<blockquote>Множитель: <b>x{coef}</b> | Зачислено: <b>+{win:.2f} $</b>\n\n"
        f"Hash: <code>{data['hash']}</code>\nСоль: <code>{data['salt']}</code></blockquote>"
    )
    await safe_edit(call, text, build_tower_kb(data["floor"], data["grid"], False, 0))