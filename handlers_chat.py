# handlers_chat.py
import math
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from database import (
    get_user, register_user, transfer_balance,
    get_chat_jackpot, claim_chat_jackpot, get_top_players, set_chat_link
)
from config import EMOJI, ICON_IDS, TOP_NUMBERS, ADMIN_IDS
from utils import safe_edit, log_event

chat_router = Router()


def is_chat_group(msg: Message) -> bool:
    return msg.chat.type in ["group", "supergroup"]


def top_categories_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Оборот", callback_data="top_cat_turnover", style="primary"),
            InlineKeyboardButton(text="Баланс", callback_data="top_cat_balance", style="success", icon_custom_emoji_id=ICON_IDS["cash"])
        ],
        [
            InlineKeyboardButton(text="Рефералы", callback_data="top_cat_referrals", style="primary"),
            InlineKeyboardButton(text="Чаты по обороту", callback_data="top_cat_chats", style="primary", icon_custom_emoji_id=ICON_IDS["fire"])
        ]
    ])


def chat_games_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Мины (Mines)", callback_data="game_mines", style="primary", icon_custom_emoji_id=ICON_IDS["mine"]),
            InlineKeyboardButton(text="Башня (Tower)", callback_data="game_tower", style="primary", icon_custom_emoji_id=ICON_IDS["rocket"])
        ],
        [
            InlineKeyboardButton(text="Кости (Dice)", callback_data="game_dice", style="primary", icon_custom_emoji_id=ICON_IDS["fire"]),
            InlineKeyboardButton(text="⚽ Спорт", callback_data="game_sport", style="primary")
        ]
    ])


@chat_router.message(F.chat.type.in_(["group", "supergroup"]), F.text.lower().in_(["игры", "/games", "games"]))
async def cmd_chat_games_menu(message: Message):
    text = (
        f"{EMOJI['fire']} <b>Игровое меню NiceBet</b>\n\n"
        f"<blockquote>Выберите мини-игру для запуска в чате!\n\n"
        f"<i>Все выигрыши зачисляются на общий баланс бота.</i></blockquote>"
    )
    await message.reply(text, reply_markup=chat_games_menu_kb(), parse_mode="HTML")


@chat_router.message(F.text.lower().in_(["топ", "/top", "top"]))
@chat_router.callback_query(F.data == "open_top")
async def show_top_menu(event):
    text = f"{EMOJI['fire']} | <b>Топ игроков месяца</b>\n\n<blockquote>• Выберите категорию:</blockquote>"
    if isinstance(event, Message):
        await event.reply(text, reply_markup=top_categories_kb(), parse_mode="HTML")
    else:
        await safe_edit(event, text, top_categories_kb())


@chat_router.callback_query(F.data.startswith("top_cat_"))
async def render_top_category(call: CallbackQuery):
    cat = call.data.replace("top_cat_", "")
    cat_names = {"turnover": "Оборот ставок", "balance": "Игровой баланс",
                 "referrals": "Приглашённые рефералы", "chats": "Оборот игровых чатов"}
    rows = await get_top_players(cat, limit=10)
    lines = [f"{EMOJI['fire']} | <b>Топ-10: {cat_names.get(cat, cat)}</b>\n", "<blockquote>"]
    if not rows:
        lines.append("Список лидеров пуст.")
    else:
        for i, row in enumerate(rows, start=1):
            icon = TOP_NUMBERS.get(i, f"{i}.")
            if cat == "chats":
                name = row['chat_title'] or f"Чат {row['chat_id']}"
                val_str = f"{row['val']:.2f} $"
                lines.append(f"{icon} — <b>{name}</b> — <b>{val_str}</b>")
            else:
                nick = f"@{row['username']}" if row['username'] else f"id:{row['user_id']}"
                val = row['val']
                val_str = f"{val:.2f} $" if cat in ["turnover", "balance"] else f"{int(val)} чел."
                lines.append(f"{icon} — {nick} — <b>{val_str}</b>")
    lines.append("</blockquote>")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Оборот", callback_data="top_cat_turnover", style="primary"),
            InlineKeyboardButton(text="Баланс", callback_data="top_cat_balance", style="success", icon_custom_emoji_id=ICON_IDS["cash"])
        ],
        [
            InlineKeyboardButton(text="Рефералы", callback_data="top_cat_referrals", style="primary"),
            InlineKeyboardButton(text="Чаты", callback_data="top_cat_chats", style="primary", icon_custom_emoji_id=ICON_IDS["fire"])
        ],
        [InlineKeyboardButton(text="Назад к категориям", callback_data="open_top", style="danger", icon_custom_emoji_id=ICON_IDS["cross"])]
    ])

    # Если это топ чатов — добавим кнопки-ссылки на каждый чат
    if cat == "chats" and rows:
        rows_buttons = []
        for i, row in enumerate(rows, start=1):
            link = row['chat_link'] if 'chat_link' in row.keys() else None
            if link:
                rows_buttons.append([
                    InlineKeyboardButton(
                        text=f"{i}. {row['chat_title'] or row['chat_id']}",
                        url=link,
                        style="primary"
                    )
                ])
        if rows_buttons:
            kb = InlineKeyboardMarkup(inline_keyboard=rows_buttons + [
                [
                    InlineKeyboardButton(text="Оборот", callback_data="top_cat_turnover", style="primary"),
                    InlineKeyboardButton(text="Баланс", callback_data="top_cat_balance", style="success", icon_custom_emoji_id=ICON_IDS["cash"])
                ],
                [
                    InlineKeyboardButton(text="Рефералы", callback_data="top_cat_referrals", style="primary"),
                    InlineKeyboardButton(text="Чаты", callback_data="top_cat_chats", style="primary", icon_custom_emoji_id=ICON_IDS["fire"])
                ],
                [InlineKeyboardButton(text="Назад к категориям", callback_data="open_top", style="danger", icon_custom_emoji_id=ICON_IDS["cross"])]
            ])

    await safe_edit(call, "\n".join(lines), kb)


# /send — перевод между игроками
@chat_router.message(Command("send"))
async def cmd_chat_send(message: Message, bot: Bot):
    if not is_chat_group(message):
        return
    uid = message.from_user.id
    sender = await get_user(uid)
    if not sender:
        await register_user(uid, message.from_user.username or "")
        sender = await get_user(uid)
    if not message.reply_to_message or message.reply_to_message.from_user.is_bot:
        return await message.reply(
            "⚠️ <b>Как перевести:</b>\n"
            "<blockquote>Ответьте на сообщение игрока: <code>/send СУММА</code></blockquote>",
            parse_mode="HTML"
        )
    target_user = message.reply_to_message.from_user
    if target_user.id == uid:
        return await message.reply("❌ Нельзя переводить себе!")
    target_in_db = await get_user(target_user.id)
    if not target_in_db:
        await register_user(target_user.id, target_user.username or "")
    args = message.text.split()
    if len(args) < 2:
        return await message.reply("⚠️ Укажите сумму: <code>/send 1</code>", parse_mode="HTML")
    try:
        amount = float(args[1].replace("$", "").replace(",", ".").strip())
        if math.isnan(amount) or math.isinf(amount) or amount < 0.05:
            return await message.reply("❌ Минимум: <b>0.05 $</b>", parse_mode="HTML")
        amount = round(amount, 2)
    except ValueError:
        return await message.reply("❌ Неверный формат суммы.")
    success = await transfer_balance(uid, target_user.id, amount)
    if not success:
        return await message.reply(
            f"❌ <b>Недостаточно средств!</b>\n"
            f"<blockquote>Ваш баланс: <b>{sender['balance']:.2f} $</b></blockquote>",
            parse_mode="HTML"
        )
    await message.reply(
        f"{EMOJI['cash']} <b>Перевод выполнен!</b>\n\n"
        f"<blockquote>От: <b>{message.from_user.first_name}</b>\n"
        f"Кому: <b>{target_user.first_name}</b>\n"
        f"Сумма: <b>+{amount:.2f} $</b></blockquote>",
        parse_mode="HTML"
    )
    await log_event(bot, "Перевод игроку", message.from_user,
                    f"→ @{target_user.username or target_user.id}\nСумма: {amount:.2f} $")


@chat_router.message(F.text.lower().in_(["джекпот", "jackpot", "/jackpot"]))
async def show_chat_jackpot(message: Message):
    if not is_chat_group(message):
        return
    chat_id = message.chat.id
    chat_title = message.chat.title or "Игровой Чат"
    current_jackpot = await get_chat_jackpot(chat_id, chat_title)
    # Автоматически сохраняем ссылку на чат (если у чата есть username)
    if message.chat.username:
        await set_chat_link(chat_id, f"https://t.me/{message.chat.username}")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Вывести джекпот", callback_data=f"claim_jp_{chat_id}", style="success", icon_custom_emoji_id=ICON_IDS["cash"])]
    ])
    text = (
        f"🔥 | <b>Джекпот {chat_title}</b>\n\n<blockquote>"
        f"• <b>Баланс:</b> <code>{current_jackpot:.2f} $</code>\n"
        f"• <b>Мин. вывод:</b> <code>0.50 $</code>\n\n"
        f"<i>💡 Пул пополняется 0.5% от проигранных ставок. Вывод — только владельцу чата.</i></blockquote>"
    )
    await message.reply(text, reply_markup=kb, parse_mode="HTML")


@chat_router.callback_query(F.data.startswith("claim_jp_"))
async def process_claim_jackpot(call: CallbackQuery, bot: Bot):
    chat_id = int(call.data.split("_")[2])
    uid = call.from_user.id
    try:
        member = await bot.get_chat_member(chat_id, uid)
        if member.status != "creator":
            return await call.answer("⛔ Только создатель чата может забрать!", show_alert=True)
    except Exception:
        return await call.answer("❌ Ошибка проверки прав.", show_alert=True)
    owner = await get_user(uid)
    if not owner:
        await register_user(uid, call.from_user.username or "")
    claimed_amount = await claim_chat_jackpot(chat_id, uid)
    if claimed_amount <= 0:
        return await call.answer("❌ Минимум для вывода — 0.50 $!", show_alert=True)
    chat_title = call.message.chat.title or "Игровой Чат"
    updated_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Вывести джекпот", callback_data=f"claim_jp_{chat_id}", style="success", icon_custom_emoji_id=ICON_IDS["cash"])]
    ])
    new_text = (
        f"🔥 | <b>Джекпот {chat_title}</b>\n\n<blockquote>"
        f"• <b>Баланс:</b> <code>0.00 $</code>\n"
        f"• <b>Мин. вывод:</b> <code>0.50 $</code>\n\n"
        f"🎉 Владелец забрал: <b>+{claimed_amount:.2f} $</b>!</blockquote>"
    )
    await safe_edit(call, new_text, updated_kb)
    await call.answer(f"✅ {claimed_amount:.2f}$ на ваш баланс!", show_alert=True)
    await log_event(bot, "Джекпот чата", call.from_user, f"Сумма: +{claimed_amount:.2f} $")


# Автоматическое сохранение ссылки при любом сообщении в чате
@chat_router.message(F.chat.type.in_(["group", "supergroup"]))
async def auto_save_chat_link(message: Message):
    if message.chat.username:
        await set_chat_link(message.chat.id, f"https://t.me/{message.chat.username}")