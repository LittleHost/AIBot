# handlers_sport_admin.py
import aiosqlite
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import (
    db_add_sport_event, db_get_active_sport_events, db_deactivate_sport_event,
    db_get_sport_event, db_update_sport_event_field,
    db_get_pending_sport_bets, db_resolve_sport_bet, DB_PATH
)
from config import ADMIN_IDS, ICON_IDS
from utils import safe_edit, log_event

admin_sport_router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


class AdminSportStates(StatesGroup):
    waiting_team1 = State()
    waiting_team2 = State()
    waiting_coef1 = State()
    waiting_coef2 = State()
    waiting_description = State()
    waiting_ai_prediction = State()
    waiting_lineups = State()
    waiting_new_coef1 = State()
    waiting_new_coef2 = State()
    waiting_new_lineups = State()
    waiting_new_desc = State()


def admin_sport_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить событие", callback_data="adm_sport_add", style="success", icon_custom_emoji_id=ICON_IDS["check"])],
        [InlineKeyboardButton(text="📋 Активные события", callback_data="adm_sport_list", style="primary")],
        [InlineKeyboardButton(text="🎯 Ожидающие ставки", callback_data="adm_sport_pending", style="primary")],
        [InlineKeyboardButton(text="⬅️ В админ-панель", callback_data="adm_main_menu", style="danger")]
    ])


@admin_sport_router.callback_query(F.data == "adm_sport_menu")
async def adm_sport_menu(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    await safe_edit(call, "⚽ <b>Управление ставками на спорт</b>", admin_sport_menu_kb())


@admin_sport_router.callback_query(F.data == "adm_sport_add")
async def adm_sport_add_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.set_state(AdminSportStates.waiting_team1)
    await safe_edit(call,
        "⚽ <b>Добавление события</b>\n\n<blockquote>Первая команда:</blockquote>",
        InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data="adm_sport_menu", style="danger")]])
    )


@admin_sport_router.message(AdminSportStates.waiting_team1)
async def adm_sport_team1(message: Message, state: FSMContext):
    await state.update_data(team1=message.text.strip())
    await state.set_state(AdminSportStates.waiting_team2)
    await message.reply("Введите вторую команду:")


@admin_sport_router.message(AdminSportStates.waiting_team2)
async def adm_sport_team2(message: Message, state: FSMContext):
    await state.update_data(team2=message.text.strip())
    await state.set_state(AdminSportStates.waiting_coef1)
    await message.reply("Коэффициент для первой команды (например 1.85):")


@admin_sport_router.message(AdminSportStates.waiting_coef1)
async def adm_sport_coef1(message: Message, state: FSMContext):
    try:
        coef = float(message.text.replace(",", ".").strip())
    except ValueError:
        return await message.reply("❌ Число:")
    await state.update_data(coef1=coef)
    await state.set_state(AdminSportStates.waiting_coef2)
    await message.reply("Коэффициент для второй команды:")


@admin_sport_router.message(AdminSportStates.waiting_coef2)
async def adm_sport_coef2(message: Message, state: FSMContext):
    try:
        coef = float(message.text.replace(",", ".").strip())
    except ValueError:
        return await message.reply("❌ Число:")
    await state.update_data(coef2=coef)
    await state.set_state(AdminSportStates.waiting_description)
    await message.reply("Описание (или '-' чтобы пропустить):")


@admin_sport_router.message(AdminSportStates.waiting_description)
async def adm_sport_desc(message: Message, state: FSMContext):
    desc = "" if message.text.strip() == "-" else message.text.strip()
    await state.update_data(description=desc)
    await state.set_state(AdminSportStates.waiting_ai_prediction)
    await message.reply("Прогноз от ИИ (или '-' чтобы пропустить):")


@admin_sport_router.message(AdminSportStates.waiting_ai_prediction)
async def adm_sport_ai(message: Message, state: FSMContext):
    ai = "" if message.text.strip() == "-" else message.text.strip()
    await state.update_data(ai_prediction=ai)
    await state.set_state(AdminSportStates.waiting_lineups)
    await message.reply("Составы (или '-' чтобы пропустить):")


@admin_sport_router.message(AdminSportStates.waiting_lineups)
async def adm_sport_lineups(message: Message, state: FSMContext):
    lineups = "" if message.text.strip() == "-" else message.text.strip()
    data = await state.get_data()
    await state.clear()
    event_id = await db_add_sport_event(
        team1=data["team1"], team2=data["team2"],
        coef1=data["coef1"], coef2=data["coef2"],
        description=data.get("description", ""),
        ai_prediction=data.get("ai_prediction", ""),
        lineups=lineups
    )
    await message.reply(
        f"✅ <b>Событие добавлено!</b>\n<blockquote>ID: <code>{event_id}</code>\n"
        f"{data['team1']} — {data['team2']}\n"
        f"Коэф: {data['coef1']} / {data['coef2']}</blockquote>",
        reply_markup=admin_sport_menu_kb(), parse_mode="HTML"
    )


@admin_sport_router.callback_query(F.data == "adm_sport_list")
async def adm_sport_list(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    events = await db_get_active_sport_events()
    if not events:
        return await safe_edit(call, "📋 Активных событий нет.",
                               InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="adm_sport_menu", style="danger")]]))
    kb = []
    for ev in events:
        kb.append([InlineKeyboardButton(
            text=f"⚙️ {ev['team1']} — {ev['team2']}",
            callback_data=f"adm_sport_manage_{ev['id']}", style="primary"
        )])
    kb.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="adm_sport_menu", style="danger")])
    await safe_edit(call, "📋 <b>Активные события</b>\n<blockquote>Выберите событие:</blockquote>",
                    InlineKeyboardMarkup(inline_keyboard=kb))


@admin_sport_router.callback_query(F.data.startswith("adm_sport_manage_"))
async def adm_sport_manage(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    event_id = int(call.data.replace("adm_sport_manage_", ""))
    ev = await db_get_sport_event(event_id)
    if not ev:
        return await call.answer("❌ Событие не найдено.", show_alert=True)

    desc = ev["description"] or "—"
    ai = ev["ai_prediction"] or "—"
    lineups = ev["lineups"] or "—"

    text = (
        f"⚙️ <b>Управление событием #{event_id}</b>\n\n<blockquote>"
        f"⚽ {ev['team1']} — {ev['team2']}\n\n"
        f"📊 Коэффициенты:\n"
        f"• {ev['team1']}: <b>x{ev['coef1']}</b>\n"
        f"• {ev['team2']}: <b>x{ev['coef2']}</b>\n\n"
        f"📝 Описание:\n{desc}\n\n"
        f"🤖 Прогноз ИИ:\n{ai}\n\n"
        f"👥 Составы:\n{lineups}"
        f"</blockquote>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Изменить коэффициенты", callback_data=f"adm_sport_editcoef_{event_id}", style="primary")],
        [InlineKeyboardButton(text="📝 Изменить составы", callback_data=f"adm_sport_editlineups_{event_id}", style="primary")],
        [InlineKeyboardButton(text="🔄 Изменить описание", callback_data=f"adm_sport_editdesc_{event_id}", style="primary")],
        [InlineKeyboardButton(text="❌ Деактивировать", callback_data=f"adm_sport_del_{event_id}", style="danger")],
        [InlineKeyboardButton(text="⬅️ К списку", callback_data="adm_sport_list", style="danger")]
    ])
    await safe_edit(call, text, kb)


@admin_sport_router.callback_query(F.data.startswith("adm_sport_editcoef_"))
async def adm_sport_edit_coef_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    event_id = int(call.data.replace("adm_sport_editcoef_", ""))
    ev = await db_get_sport_event(event_id)
    if not ev:
        return await call.answer("❌ Событие не найдено.", show_alert=True)
    await state.update_data(edit_event_id=event_id)
    await state.set_state(AdminSportStates.waiting_new_coef1)
    await safe_edit(call,
        f"✏️ <b>Изменение коэффициентов</b>\n\n<blockquote>"
        f"Команды: <b>{ev['team1']}</b> — <b>{ev['team2']}</b>\n\n"
        f"Текущие:\n"
        f"• {ev['team1']}: <b>x{ev['coef1']}</b>\n"
        f"• {ev['team2']}: <b>x{ev['coef2']}</b>\n\n"
        f"Введите новый коэффициент для <b>{ev['team1']}</b>:"
        f"</blockquote>",
        InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data=f"adm_sport_manage_{event_id}", style="danger")]])
    )


@admin_sport_router.message(AdminSportStates.waiting_new_coef1)
async def adm_sport_new_coef1(message: Message, state: FSMContext):
    try:
        coef = float(message.text.replace(",", ".").strip())
        if coef <= 1.0:
            return await message.reply("❌ Коэффициент должен быть > 1.0")
    except ValueError:
        return await message.reply("❌ Введите число:")
    await state.update_data(new_coef1=coef)
    await state.set_state(AdminSportStates.waiting_new_coef2)
    data = await state.get_data()
    ev = await db_get_sport_event(data["edit_event_id"])
    await message.reply(f"Введите новый коэффициент для <b>{ev['team2']}</b>:", parse_mode="HTML")


@admin_sport_router.message(AdminSportStates.waiting_new_coef2)
async def adm_sport_new_coef2(message: Message, state: FSMContext):
    try:
        coef = float(message.text.replace(",", ".").strip())
        if coef <= 1.0:
            return await message.reply("❌ Коэффициент должен быть > 1.0")
    except ValueError:
        return await message.reply("❌ Введите число:")
    data = await state.get_data()
    event_id = data["edit_event_id"]
    coef1 = data["new_coef1"]
    await db_update_sport_event_field(event_id, "coef1", coef1)
    await db_update_sport_event_field(event_id, "coef2", coef)
    await state.clear()
    await message.reply(
        f"✅ <b>Коэффициенты обновлены!</b>\n<blockquote>Новые значения: <b>x{coef1}</b> / <b>x{coef}</b></blockquote>",
        reply_markup=admin_sport_menu_kb(), parse_mode="HTML"
    )


@admin_sport_router.callback_query(F.data.startswith("adm_sport_editlineups_"))
async def adm_sport_edit_lineups_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    event_id = int(call.data.replace("adm_sport_editlineups_", ""))
    ev = await db_get_sport_event(event_id)
    if not ev:
        return await call.answer("❌ Событие не найдено.", show_alert=True)
    await state.update_data(edit_event_id=event_id)
    await state.set_state(AdminSportStates.waiting_new_lineups)
    await safe_edit(call,
        f"📝 <b>Изменение составов</b>\n\n<blockquote>"
        f"Команды: <b>{ev['team1']}</b> — <b>{ev['team2']}</b>\n\n"
        f"Текущие:\n{ev['lineups'] or '—'}\n\n"
        f"Введите новые составы (или '-' чтобы очистить):</blockquote>",
        InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data=f"adm_sport_manage_{event_id}", style="danger")]])
    )


@admin_sport_router.message(AdminSportStates.waiting_new_lineups)
async def adm_sport_new_lineups(message: Message, state: FSMContext):
    lineups = "" if message.text.strip() == "-" else message.text.strip()
    data = await state.get_data()
    event_id = data["edit_event_id"]
    await db_update_sport_event_field(event_id, "lineups", lineups)
    await state.clear()
    await message.reply("✅ Составы обновлены!", reply_markup=admin_sport_menu_kb())


@admin_sport_router.callback_query(F.data.startswith("adm_sport_editdesc_"))
async def adm_sport_edit_desc_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    event_id = int(call.data.replace("adm_sport_editdesc_", ""))
    ev = await db_get_sport_event(event_id)
    if not ev:
        return await call.answer("❌ Событие не найдено.", show_alert=True)
    await state.update_data(edit_event_id=event_id)
    await state.set_state(AdminSportStates.waiting_new_desc)
    await safe_edit(call,
        f"🔄 <b>Изменение описания</b>\n\n<blockquote>"
        f"Команды: <b>{ev['team1']}</b> — <b>{ev['team2']}</b>\n\n"
        f"Текущее:\n{ev['description'] or '—'}\n\n"
        f"Введите новое описание (или '-' чтобы очистить):</blockquote>",
        InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data=f"adm_sport_manage_{event_id}", style="danger")]])
    )


@admin_sport_router.message(AdminSportStates.waiting_new_desc)
async def adm_sport_new_desc(message: Message, state: FSMContext):
    desc = "" if message.text.strip() == "-" else message.text.strip()
    data = await state.get_data()
    event_id = data["edit_event_id"]
    await db_update_sport_event_field(event_id, "description", desc)
    await state.clear()
    await message.reply("✅ Описание обновлено!", reply_markup=admin_sport_menu_kb())


@admin_sport_router.callback_query(F.data.startswith("adm_sport_del_"))
async def adm_sport_deactivate(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    event_id = int(call.data.replace("adm_sport_del_", ""))
    await db_deactivate_sport_event(event_id)
    await call.answer("✅ Деактивировано.", show_alert=True)
    await adm_sport_list(call)


@admin_sport_router.callback_query(F.data == "adm_sport_pending")
async def adm_sport_pending(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    bets = await db_get_pending_sport_bets()
    if not bets:
        return await safe_edit(call, "🎯 Нет ожидающих ставок.",
                               InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="adm_sport_menu", style="danger")]]))
    kb = []
    for b in bets:
        kb.append([InlineKeyboardButton(
            text=f"#{b['id']} | {b['team1']}—{b['team2']} | {b['amount']:.2f}$",
            callback_data=f"adm_sport_res_{b['id']}", style="primary"
        )])
    kb.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="adm_sport_menu", style="danger")])
    await safe_edit(call, "🎯 <b>Ожидающие ставки</b>", InlineKeyboardMarkup(inline_keyboard=kb))


@admin_sport_router.callback_query(F.data.startswith("adm_sport_res_"))
async def adm_sport_resolve(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    bet_id = int(call.data.replace("adm_sport_res_", ""))
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Выигрыш", callback_data=f"adm_sport_won_{bet_id}", style="success"),
            InlineKeyboardButton(text="❌ Проигрыш", callback_data=f"adm_sport_lost_{bet_id}", style="danger")
        ],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="adm_sport_pending", style="danger")]
    ])
    await safe_edit(call, f"🎯 <b>Расчёт ставки #{bet_id}</b>\n\n<blockquote>Выберите результат:</blockquote>", kb)


@admin_sport_router.callback_query(F.data.startswith("adm_sport_won_"))
async def adm_sport_won(call: CallbackQuery, bot: Bot):
    if not is_admin(call.from_user.id):
        return
    bet_id = int(call.data.replace("adm_sport_won_", ""))
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM sport_bets WHERE id = ?", (bet_id,)) as cur:
            pre_bet = await cur.fetchone()
        if pre_bet:
            async with db.execute("SELECT team1, team2 FROM sport_events WHERE id = ?", (pre_bet["event_id"],)) as cur:
                ev = await cur.fetchone()
        else:
            ev = None
    team_name = "—"
    if ev and pre_bet:
        team_name = ev["team1"] if pre_bet["bet_on"] == "1" else ev["team2"]

    result = await db_resolve_sport_bet(bet_id, True)
    if result:
        try:
            await bot.send_message(
                result["user_id"],
                f"🎉 <b>Ставка на спорт ВЫИГРАЛА!</b>\n\n<blockquote>"
                f"Айди ставки: <code>{bet_id}</code>\n"
                f"Ставка на: <b>{team_name}</b>\n"
                f"Сумма: <b>{result['amount']:.2f} $</b>\n"
                f"Коэффициент: <b>x{result['coef']}</b>\n\n"
                f"Выплата: <b>+{result['payout']:.2f} $</b>\n\n"
                f"Удачи 🍀</blockquote>",
                parse_mode="HTML"
            )
        except Exception:
            pass
        await call.answer(f"✅ Выигрыш! Начислено {result['payout']:.2f}$", show_alert=True)
        await log_event(bot, "Спорт: Выигрыш", call.from_user,
                        f"Ставка #{bet_id}, выплата +{result['payout']:.2f} $")
    else:
        await call.answer("❌ Ошибка.", show_alert=True)
    await adm_sport_pending(call)


@admin_sport_router.callback_query(F.data.startswith("adm_sport_lost_"))
async def adm_sport_lost(call: CallbackQuery, bot: Bot):
    if not is_admin(call.from_user.id):
        return
    bet_id = int(call.data.replace("adm_sport_lost_", ""))
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM sport_bets WHERE id = ?", (bet_id,)) as cur:
            pre_bet = await cur.fetchone()
        if pre_bet:
            async with db.execute("SELECT team1, team2 FROM sport_events WHERE id = ?", (pre_bet["event_id"],)) as cur:
                ev = await cur.fetchone()
        else:
            ev = None
    team_name = "—"
    if ev and pre_bet:
        team_name = ev["team1"] if pre_bet["bet_on"] == "1" else ev["team2"]

    result = await db_resolve_sport_bet(bet_id, False)
    if result:
        try:
            await bot.send_message(
                result["user_id"],
                f"😔 <b>Ставка на спорт ПРОИГРАЛА</b>\n\n<blockquote>"
                f"Айди ставки: <code>{bet_id}</code>\n"
                f"Ставка на: <b>{team_name}</b>\n"
                f"Сумма: <b>{result['amount']:.2f} $</b>\n"
                f"Коэффициент: <b>x{result['coef']}</b>\n\n"
                f"Удачи в следующий раз 🍀</blockquote>",
                parse_mode="HTML"
            )
        except Exception:
            pass
        await call.answer("Ставка рассчитана.", show_alert=True)
        await log_event(bot, "Спорт: Проигрыш", call.from_user,
                        f"Ставка #{bet_id}, потеряно {result['amount']:.2f} $")
    else:
        await call.answer("❌ Ошибка.", show_alert=True)
    await adm_sport_pending(call)