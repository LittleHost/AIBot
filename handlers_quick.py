# handlers_quick.py
import math
import asyncio
from aiogram import Router, F, Bot
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from database import get_user, register_user, set_user_setting, update_balance, add_turnover, record_game
from config import EMOJI, ICON_IDS
from utils import log_event

quick_router = Router()
MIN_BET = 0.05


@quick_router.message(F.text.regexp(r"^(\d+(?:[\.,]\d+)?)\$$"))
async def quick_change_bet(message: Message):
    uid = message.from_user.id
    user = await get_user(uid)
    if not user:
        await register_user(uid, message.from_user.username or "")
        user = await get_user(uid)
    raw_val = message.text[:-1].replace(",", ".").strip()
    try:
        new_bet = float(raw_val)
        if math.isnan(new_bet) or math.isinf(new_bet) or new_bet <= 0:
            return await message.reply("❌ Некорректная сумма!")
        new_bet = round(new_bet, 2)
        if new_bet < MIN_BET:
            return await message.reply(f"❌ Минимум: <b>{MIN_BET:.2f} $</b>", parse_mode="HTML")
    except ValueError:
        return
    await set_user_setting(uid, "selected_bet", new_bet)
    await message.reply(
        f"{EMOJI['cash']} <b>Ставка обновлена!</b>\n\n<blockquote>Новая ставка: <b>{new_bet:.2f} $</b></blockquote>",
        parse_mode="HTML"
    )


@quick_router.message(F.text.lower().in_(["мины", "мина", "mines", "mine"]))
async def quick_mines_table(message: Message):
    uid = message.from_user.id
    user = await get_user(uid)
    if not user:
        await register_user(uid, message.from_user.username or "")
        user = await get_user(uid)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Начать играть", callback_data="mines_play_round", style="success", icon_custom_emoji_id=ICON_IDS["check"])],
        [InlineKeyboardButton(text=f"Мин: {user['selected_mines']}", callback_data="change_mines_cnt", style="primary", icon_custom_emoji_id=ICON_IDS["mine"])],
        [InlineKeyboardButton(text="Меню игр", callback_data="open_games", icon_custom_emoji_id=ICON_IDS["cross"])]
    ])
    text = (
        f"{EMOJI['mine']} <b>МИНЫ</b>\n\n<blockquote>"
        f"Баланс: <b>{user['balance']:.2f}</b> {EMOJI['cash']}\n"
        f"Ставка: <b>{user['selected_bet']:.2f}</b> {EMOJI['cash']}\n"
        f"Мин: <b>{user['selected_mines']}</b>\n\n"
        f"{EMOJI['shield']} Provably Fair SHA-256</blockquote>"
    )
    await message.reply(text, reply_markup=kb, parse_mode="HTML")


@quick_router.message(F.text.lower().in_(["башня", "башни", "tower", "towers"]))
async def quick_tower_table(message: Message):
    uid = message.from_user.id
    user = await get_user(uid)
    if not user:
        await register_user(uid, message.from_user.username or "")
        user = await get_user(uid)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Начать подъем", callback_data="tower_play_round", style="success", icon_custom_emoji_id=ICON_IDS["rocket"])],
        [InlineKeyboardButton(text=f"Сложность: {user['selected_traps']} лов/ряд", callback_data="change_traps_cnt", style="primary")],
        [InlineKeyboardButton(text="Меню игр", callback_data="open_games", icon_custom_emoji_id=ICON_IDS["cross"])]
    ])
    text = (
        f"{EMOJI['tower']} <b>БАШНЯ</b>\n\n<blockquote>"
        f"Баланс: <b>{user['balance']:.2f}</b> {EMOJI['cash']}\n"
        f"Ставка: <b>{user['selected_bet']:.2f}</b> {EMOJI['cash']}\n"
        f"Сложность: <b>{user['selected_traps']} ловушек</b></blockquote>"
    )
    await message.reply(text, reply_markup=kb, parse_mode="HTML")


async def execute_quick_dice(message: Message, mode_title, dice_count, eval_fn):
    uid = message.from_user.id
    user = await get_user(uid)
    if not user:
        await register_user(uid, message.from_user.username or "")
        user = await get_user(uid)
    bet = user["selected_bet"]
    if user["ban_games"]:
        return await message.reply("❌ Игры заблокированы.")
    if user["balance"] < bet:
        return await message.reply(
            f"❌ Недостаточно!\n<blockquote>Баланс: <b>{user['balance']:.2f} $</b> | Ставка: <b>{bet:.2f} $</b></blockquote>",
            parse_mode="HTML"
        )
    await update_balance(uid, -bet)
    await add_turnover(uid, bet)
    is_group = message.chat.type in ["group", "supergroup"]
    c_id = message.chat.id if is_group else 0
    c_title = message.chat.title if is_group else ""
    start_notice = await message.reply(
        f"🎲 <b>Бросок: {mode_title}</b>\n"
        f"<blockquote>Игрок: <b>{message.from_user.first_name}</b> | Ставка: <b>{bet:.2f} $</b></blockquote>",
        parse_mode="HTML"
    )
    dices = []
    for _ in range(dice_count):
        d_msg = await message.answer_dice(emoji="🎲")
        dices.append(d_msg.dice.value)
    await asyncio.sleep(3.6 if dice_count == 1 else 4.2)
    is_win, multiplier, details = eval_fn(dices)
    if is_win:
        payout = round(bet * multiplier, 2)
        await update_balance(uid, payout)
        await record_game(uid, f"Быстрый Куб: {mode_title}", bet, payout, True, chat_id=c_id, chat_title=c_title)
        result_text = (
            f"{EMOJI['trophy']} <b>ПОБЕДА!</b>\n\n<blockquote>"
            f"Режим: <b>{mode_title}</b>\n"
            f"Результат: <b>{details}</b>\n"
            f"Множитель: <b>x{multiplier}</b>\n"
            f"Выигрыш: <b>+{payout:.2f}</b> {EMOJI['cash']}</blockquote>"
        )
    else:
        await record_game(uid, f"Быстрый Куб: {mode_title}", bet, 0.0, False, chat_id=c_id, chat_title=c_title)
        result_text = (
            f"{EMOJI['cross']} <b>ПРОИГРЫШ</b>\n\n<blockquote>"
            f"Режим: <b>{mode_title}</b>\n"
            f"Результат: <b>{details}</b>\n"
            f"Ставка: <b>-{bet:.2f}</b> {EMOJI['cash']}</blockquote>"
        )
    await start_notice.reply(result_text, parse_mode="HTML")


@quick_router.message(F.text.lower().startswith("куб"))
async def parse_quick_cube(message: Message):
    text = message.text.lower().strip()
    parts = text.split()
    if len(parts) < 2:
        return await message.reply(
            "🎲 <b>Быстрые команды:</b>\n\n<blockquote>"
            "• <code>Куб больше</code> / <code>Куб меньше</code> (x1.9)\n"
            "• <code>Куб чет</code> / <code>Куб нечет</code> (x1.9)\n"
            "• <code>Куб 5</code> (x6.0)\n"
            "• <code>Куб 7+</code> / <code>Куб 7-</code> / <code>Куб 7=</code>\n"
            "• <code>Куб 18+</code> / <code>Куб 18-</code></blockquote>",
            parse_mode="HTML"
        )
    action = parts[1]
    if action in ["больше", ">", "high", "бол"]:
        return await execute_quick_dice(message, "Больше (4-6)", 1, lambda d: (d[0] >= 4, 1.9, f"Выпало {d[0]}"))
    if action in ["меньше", "<", "low", "мен"]:
        return await execute_quick_dice(message, "Меньше (1-3)", 1, lambda d: (d[0] <= 3, 1.9, f"Выпало {d[0]}"))
    if action in ["чет", "чёт", "even"]:
        return await execute_quick_dice(message, "Чётное", 1, lambda d: (d[0] % 2 == 0, 1.9, f"Выпало {d[0]}"))
    if action in ["нечет", "нечёт", "odd"]:
        return await execute_quick_dice(message, "Нечётное", 1, lambda d: (d[0] % 2 != 0, 1.9, f"Выпало {d[0]}"))
    if action in ["7+", "7-", "7="]:
        def eval_seven(d):
            s = d[0] + d[1]
            desc = f"{d[0]} + {d[1]} = {s}"
            if action == "7+" and s > 7: return True, 2.7, desc
            if action == "7-" and s < 7: return True, 2.7, desc
            if action == "7=" and s == 7: return True, 6.0, desc
            return False, 0.0, desc
        return await execute_quick_dice(message, f"Сумма {action}", 2, eval_seven)
    if action in ["18+", "18-"]:
        def eval_mult18(d):
            p = d[0] * d[1]
            desc = f"{d[0]} * {d[1]} = {p}"
            if action == "18+" and p >= 18: return True, 4.0, desc
            if action == "18-" and p < 18: return True, 1.2, desc
            return False, 0.0, desc
        return await execute_quick_dice(message, f"Умножение {action}", 2, eval_mult18)
    if action.isdigit():
        val = int(action)
        if 1 <= val <= 6:
            return await execute_quick_dice(
                message, f"Число {val}", 1,
                lambda d: (d[0] == val, 6.0, f"Выпало {d[0]} (на {val})")
            )
    await message.reply("❌ Неизвестный режим.")