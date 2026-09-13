# handlers_sport.py
import math
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import (
    get_user, db_get_active_sport_events, db_get_sport_event,
    db_place_sport_bet, db_get_user_sport_bets
)
from config import EMOJI, ICON_IDS
from utils import safe_edit, log_event

sport_router = Router()


class SportBetStates(StatesGroup):
    waiting_for_amount = State()


def sport_events_kb(events) -> InlineKeyboardMarkup:
    kb = []
    for ev in events:
        kb.append([InlineKeyboardButton(
            text=f"⚽ {ev['team1']} — {ev['team2']}",
            callback_data=f"sport_view_{ev['id']}", style="primary"
        )])
    kb.append([InlineKeyboardButton(text="Назад в меню игр", callback_data="open_games", style="danger", icon_custom_emoji_id=ICON_IDS["cross"])])
    return InlineKeyboardMarkup(inline_keyboard=kb)


@sport_router.callback_query(F.data == "game_sport")
async def open_sport_menu(call: CallbackQuery):
    events = await db_get_active_sport_events()
    if not events:
        return await safe_edit(call,
            "⚽ <b>Ставки на спорт</b>\n\n"
            "<blockquote>😔 Пока нет доступных событий.\nЗагляните позже!</blockquote>",
            InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Назад в меню игр", callback_data="open_games", style="danger", icon_custom_emoji_id=ICON_IDS["cross"])]
            ])
        )
    await safe_edit(call,
        "⚽ <b>Ставки на спорт</b>\n\n<blockquote>Выберите событие:</blockquote>",
        sport_events_kb(events)
    )


@sport_router.callback_query(F.data.startswith("sport_view_"))
async def view_sport_event(call: CallbackQuery):
    event_id = int(call.data.replace("sport_view_", ""))
    ev = await db_get_sport_event(event_id)
    if not ev or not ev["is_active"]:
        return await call.answer("❌ Событие недоступно.", show_alert=True)
    desc = ev["description"] or "—"
    ai = ev["ai_prediction"] or "—"
    lineups = ev["lineups"] or "—"
    text = (
        f"⚽ <b>{ev['team1']} — {ev['team2']}</b>\n\n<blockquote>"
        f"📊 Коэффициенты:\n"
        f"• {ev['team1']}: <b>x{ev['coef1']}</b>\n"
        f"• {ev['team2']}: <b>x{ev['coef2']}</b>\n\n"
        f"📝 Описание:\n{desc}\n\n"
        f"🤖 Прогноз от ИИ:\n{ai}\n\n"
        f"👥 Составы:\n{lineups}\n\n"
        f"Удачи!</blockquote>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Ставка на {ev['team1']} (x{ev['coef1']})", callback_data=f"sport_bet_{ev['id']}_1", style="success", icon_custom_emoji_id=ICON_IDS["cash"])],
        [InlineKeyboardButton(text=f"Ставка на {ev['team2']} (x{ev['coef2']})", callback_data=f"sport_bet_{ev['id']}_2", style="success", icon_custom_emoji_id=ICON_IDS["cash"])],
        [
            InlineKeyboardButton(text="Мои ставки", callback_data="sport_my_bets", style="primary"),
            InlineKeyboardButton(text="Назад", callback_data="game_sport", style="danger", icon_custom_emoji_id=ICON_IDS["cross"])
        ]
    ])
    await safe_edit(call, text, kb)


@sport_router.callback_query(F.data.startswith("sport_bet_"))
async def ask_sport_bet_amount(call: CallbackQuery, state: FSMContext):
    parts = call.data.split("_")
    event_id = int(parts[2])
    bet_on = parts[3]
    ev = await db_get_sport_event(event_id)
    if not ev or not ev["is_active"]:
        return await call.answer("❌ Событие недоступно.", show_alert=True)
    team = ev["team1"] if bet_on == "1" else ev["team2"]
    coef = ev["coef1"] if bet_on == "1" else ev["coef2"]
    await state.update_data(sport_event_id=event_id, sport_bet_on=bet_on, sport_coef=coef, sport_team=team)
    await state.set_state(SportBetStates.waiting_for_amount)
    user = await get_user(call.from_user.id)
    text = (
        f"⚽ <b>Ставка на {team}</b>\n\n<blockquote>"
        f"Коэф: <b>x{coef}</b>\n"
        f"Баланс: <b>{user['balance']:.2f} $</b>\n\n"
        f"Введите сумму:</blockquote>"
    )
    await safe_edit(call, text, InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Отмена", callback_data="game_sport", style="danger", icon_custom_emoji_id=ICON_IDS["cross"])]
    ]))


@sport_router.message(SportBetStates.waiting_for_amount)
async def process_sport_bet_amount(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    event_id = data["sport_event_id"]
    bet_on = data["sport_bet_on"]
    coef = data["sport_coef"]
    team = data["sport_team"]
    raw = message.text.replace("$", "").replace(",", ".").strip()
    try:
        amount = float(raw)
        if math.isnan(amount) or math.isinf(amount) or amount < 0.05:
            return await message.reply("❌ Минимум: 0.05 $")
        amount = round(amount, 2)
    except ValueError:
        return await message.reply("❌ Число:")
    user = await get_user(message.from_user.id)
    if user["balance"] < amount:
        return await message.reply(f"❌ Баланс: <b>{user['balance']:.2f} $</b>", parse_mode="HTML")
    bet_id = await db_place_sport_bet(message.from_user.id, event_id, bet_on, amount, coef)
    if bet_id < 0:
        return await message.reply("❌ Ошибка размещения.")
    await state.clear()
    await message.reply(
        f"✅ <b>Ставка принята!</b>\n\n<blockquote>"
        f"Айди ставки: <code>{bet_id}</code>\n"
        f"Ставка на: <b>{team}</b>\n"
        f"Сумма: <b>{amount:.2f} $</b>\n"
        f"Коэффициент: <b>x{coef}</b>\n\n"
        f"Удачи 🍀</blockquote>",
        parse_mode="HTML"
    )
    await log_event(bot, "Ставка на спорт", message.from_user,
                    f"Ставка #{bet_id}\n{team} | {amount:.2f} $ | x{coef}")


@sport_router.callback_query(F.data == "sport_my_bets")
async def show_my_sport_bets(call: CallbackQuery):
    bets = await db_get_user_sport_bets(call.from_user.id, 10)
    if not bets:
        return await call.answer("У вас нет ставок на спорт.", show_alert=True)
    lines = ["⚽ <b>Ваши ставки:</b>\n<blockquote>"]
    for b in bets:
        status_map = {"pending": "⏳ Ожидает", "won": "🟢 Выигрыш", "lost": "🔴 Проигрыш"}
        st = status_map.get(b["status"], b["status"])
        team_name = b["team1"] if b["bet_on"] == "1" else b["team2"]
        lines.append(f"#{b['id']} | {b['team1']} — {b['team2']}\n  {b['amount']:.2f}$ на {team_name} (x{b['coef']}) | {st}")
    lines.append("</blockquote>")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад", callback_data="game_sport", style="danger", icon_custom_emoji_id=ICON_IDS["cross"])]
    ])
    await safe_edit(call, "\n".join(lines), kb)