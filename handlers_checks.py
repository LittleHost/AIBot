# handlers_checks.py
import secrets
import math
from aiogram import Router, F, Bot
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    InlineQuery, InlineQueryResultArticle, InputTextMessageContent
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import (
    get_user, db_create_check, db_get_check, db_get_user_checks,
    db_update_check_limit, db_cancel_check, db_activate_check
)
from config import EMOJI, ICON_IDS
from utils import safe_edit, log_event

checks_router = Router()

CHECK_MIN = 0.10
CHECK_MAX = 1000.00


class CheckStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_activations = State()
    waiting_for_user_target = State()
    waiting_for_turnover = State()
    waiting_for_deposits_count = State()


def checks_home_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="1️⃣ Персональный", callback_data="chk_type_personal", style="primary"),
            InlineKeyboardButton(text="2️⃣ Мультичек", callback_data="chk_type_multi", style="primary")
        ],
        [InlineKeyboardButton(text="3️⃣ Мои чеки", callback_data="chk_my_list", style="primary", icon_custom_emoji_id=ICON_IDS["cash"])],
        [InlineKeyboardButton(text="Назад в профиль", callback_data="profile", style="danger", icon_custom_emoji_id=ICON_IDS["cross"])]
    ])


async def process_start_check(message: Message, code: str, bot: Bot):
    is_prem = bool(message.from_user.is_premium)
    ok, reason, amt, creator_id = await db_activate_check(code, message.from_user.id, is_premium_user=is_prem)
    if ok:
        try:
            act_user = message.from_user
            act_name = f"@{act_user.username}" if act_user.username else act_user.first_name
            await bot.send_message(
                creator_id,
                f"🎉 <b>Ваш чек активирован!</b>\n\n<blockquote>"
                f"Пользователь: <b>{act_name}</b> (<code>{act_user.id}</code>)\n"
                f"Сумма: <b>+{amt:.2f} $</b></blockquote>",
                parse_mode="HTML"
            )
        except Exception:
            pass
        await log_event(bot, "Чек активирован", message.from_user, f"Сумма: +{amt:.2f} $")
        return await message.reply(
            f"😃 <b>Чек активирован!</b>\n\n<blockquote>Зачислено: <b>+{amt:.2f} $</b></blockquote>",
            parse_mode="HTML"
        )
    else:
        return await message.reply(reason, parse_mode="HTML")


@checks_router.inline_query(F.query.startswith("check_"))
async def inline_share_check(inline_query: InlineQuery):
    code = inline_query.query.replace("check_", "").strip()
    chk = await db_get_check(code)
    if not chk or chk["status"] != "active" or chk["activations_left"] <= 0:
        results = [InlineQueryResultArticle(
            id="check_not_found",
            title="❌ Чек не найден",
            description="Уже недействителен",
            input_message_content=InputTextMessageContent(
                message_text="❌ <b>Этот чек уже недействителен!</b>", parse_mode="HTML"
            )
        )]
        return await inline_query.answer(results, cache_time=1, is_personal=True)
    bot_info = await inline_query.bot.get_me()
    check_link = f"https://t.me/{bot_info.username}?start=check_{code}"
    limits = []
    if chk["target_username"]:
        limits.append(f"• Только для: @{chk['target_username']}")
    elif chk["target_user_id"]:
        limits.append(f"• Только для ID: <code>{chk['target_user_id']}</code>")
    if chk["only_premium"]:
        limits.append("• Только Telegram Premium ⭐")
    if chk["min_turnover"] > 0:
        limits.append(f"• Оборот от {chk['min_turnover']:.2f} $")
    if chk["min_deposits_count"] > 0:
        limits.append(f"• Депозитов от {chk['min_deposits_count']} шт.")
    limits_text = "\n" + "\n".join(limits) if limits else "\n• Без ограничений"
    text_msg = (
        f"🎁 <b>Вам отправлен чек!</b>\n\n<blockquote>"
        f"Сумма: <b>{chk['amount_per_activation']:.2f} 💰</b>\n"
        f"Активаций: <b>{chk['activations_left']}/{chk['activations_total']}</b>\n\n"
        f"<b>Условия:</b>{limits_text}</blockquote>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Забрать чек", url=check_link, style="success", icon_custom_emoji_id=ICON_IDS["cash"])]
    ])
    results = [InlineQueryResultArticle(
        id=f"chk_{code}",
        title=f"Отправить чек на {chk['amount_per_activation']:.2f} $",
        description=f"Осталось: {chk['activations_left']}/{chk['activations_total']}",
        input_message_content=InputTextMessageContent(message_text=text_msg, parse_mode="HTML"),
        reply_markup=kb
    )]
    await inline_query.answer(results, cache_time=1, is_personal=True)


@checks_router.callback_query(F.data == "open_checks_menu")
async def show_checks_menu(call: CallbackQuery):
    text = (
        f"{EMOJI['cash']} <b>Чеки</b>\n\n<blockquote>"
        f"Чеки позволяют удобно отправлять средства другому пользователю\n\n"
        f"<b>Персональный</b> — одному пользователю\n"
        f"<b>Мультичек</b> — нескольким</blockquote>"
    )
    await safe_edit(call, text, checks_home_kb())


@checks_router.callback_query(F.data == "chk_type_personal")
async def show_personal_info(call: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Создать", callback_data="chk_step_curr_personal", style="success", icon_custom_emoji_id=ICON_IDS["check"])],
        [InlineKeyboardButton(text="Назад", callback_data="open_checks_menu", style="danger", icon_custom_emoji_id=ICON_IDS["cross"])]
    ])
    await safe_edit(call,
        f"📝 <b>Персональные чеки</b>\n\n<blockquote>Создайте чек для отправки средств одному пользователю.</blockquote>",
        kb
    )


@checks_router.callback_query(F.data == "chk_type_multi")
async def show_multi_info(call: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Создать", callback_data="chk_step_curr_multi", style="success", icon_custom_emoji_id=ICON_IDS["check"])],
        [InlineKeyboardButton(text="Назад", callback_data="open_checks_menu", style="danger", icon_custom_emoji_id=ICON_IDS["cross"])]
    ])
    await safe_edit(call,
        f"📝 <b>Мультичеки</b>\n\n<blockquote>Чек на несколько активаций.</blockquote>",
        kb
    )


@checks_router.callback_query(F.data.startswith("chk_step_curr_"))
async def choose_check_currency(call: CallbackQuery, state: FSMContext):
    chk_type = call.data.replace("chk_step_curr_", "")
    await state.update_data(chk_type=chk_type)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💵 USDT", callback_data="chk_set_curr_usdt", style="success", icon_custom_emoji_id=ICON_IDS["cash"])],
        [InlineKeyboardButton(text="Отмена", callback_data="open_checks_menu", style="danger", icon_custom_emoji_id=ICON_IDS["cross"])]
    ])
    await safe_edit(call, "📝 <b>Чек</b>\n\n<blockquote>Валюта:</blockquote>", kb)


@checks_router.callback_query(F.data == "chk_set_curr_usdt")
async def ask_check_amount(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    chk_type = data.get("chk_type", "personal")
    if chk_type == "multi":
        await state.set_state(CheckStates.waiting_for_activations)
        await safe_edit(call,
            "📝 <b>Мультичек</b>\n\n<blockquote>Введите количество активаций (2-1000):</blockquote>",
            InlineKeyboardMarkup(inline_keyboard=[])
        )
    else:
        await state.update_data(chk_activations=1)
        await state.set_state(CheckStates.waiting_for_amount)
        await safe_edit(call,
            f"📝 <b>Чек</b>\n\n<blockquote>Сумма чека:\n"
            f"Макс: <b>{CHECK_MAX:.1f} 💰</b>\nМин: <b>{CHECK_MIN:.1f} 💰</b></blockquote>",
            InlineKeyboardMarkup(inline_keyboard=[])
        )


@checks_router.message(CheckStates.waiting_for_activations)
async def process_check_activations(message: Message, state: FSMContext):
    try:
        cnt = int(message.text.strip())
        if cnt < 2 or cnt > 1000:
            return await message.reply("❌ 2-1000:")
    except ValueError:
        return await message.reply("❌ Целое число:")
    await state.update_data(chk_activations=cnt)
    await state.set_state(CheckStates.waiting_for_amount)
    await message.reply(
        f"📝 <b>Мультичек ({cnt} активаций)</b>\n\n"
        f"<blockquote>Сумма на 1 активацию:\nМин: <b>{CHECK_MIN:.1f} 💰</b> | Макс: <b>{CHECK_MAX:.1f} 💰</b></blockquote>",
        parse_mode="HTML"
    )


@checks_router.message(CheckStates.waiting_for_amount)
async def process_check_amount(message: Message, state: FSMContext):
    raw_val = message.text.replace("$", "").replace(",", ".").strip()
    try:
        amount = float(raw_val)
        if math.isnan(amount) or math.isinf(amount) or amount < CHECK_MIN or amount > CHECK_MAX:
            return await message.reply(f"❌ {CHECK_MIN:.1f} — {CHECK_MAX:.1f} 💰:")
        amount = round(amount, 2)
    except ValueError:
        return await message.reply("❌ Число:")
    user = await get_user(message.from_user.id)
    data = await state.get_data()
    activations = data.get("chk_activations", 1)
    total_needed = round(amount * activations, 2)
    if user["balance"] < total_needed:
        return await message.reply(
            f"❌ Недостаточно! Требуется: <b>{total_needed:.2f} $</b> (баланс: <b>{user['balance']:.2f} $</b>)",
            parse_mode="HTML"
        )
    await state.update_data(chk_amount=amount)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data="chk_confirm_creation", style="success"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="open_checks_menu", style="danger")
        ]
    ])
    await message.reply(
        f"📝 <b>Подтверждение</b>\n\n<blockquote>Сумма: <b>{amount:.2f} 💰</b>\n"
        f"Активаций: <b>{activations}</b>\n"
        f"Списание: <b>{total_needed:.2f} 💰</b></blockquote>",
        reply_markup=kb, parse_mode="HTML"
    )


@checks_router.callback_query(F.data == "chk_confirm_creation")
async def confirm_check_create(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    amount = data["chk_amount"]
    activations = data.get("chk_activations", 1)
    chk_type = data.get("chk_type", "personal")
    check_code = secrets.token_urlsafe(16)
    ok = await db_create_check(check_code, call.from_user.id, chk_type, amount, activations)
    if not ok:
        return await safe_edit(call, "❌ Ошибка списания.",
                              InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="OK", callback_data="open_checks_menu", style="primary")]]))
    bot_info = await call.bot.get_me()
    check_url = f"t.me/{bot_info.username}?start=check_{check_code}"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Отправить", switch_inline_query=f"check_{check_code}", style="primary")],
        [InlineKeyboardButton(text="Ограничение", callback_data=f"chk_limits_{check_code}", style="primary")],
        [InlineKeyboardButton(text="Удалить", callback_data=f"chk_delete_{check_code}", style="danger")]
    ])
    text = (
        f"😃 <b>Чек создан</b>\n\n<blockquote>Сумма: <b>{amount:.2f} 💰</b>\n\n"
        f"⚠️ Не передавайте ссылку незнакомым!\n\n"
        f"Ссылка:\n<code>{check_url}</code></blockquote>"
    )
    await safe_edit(call, text, kb)


@checks_router.callback_query(F.data.startswith("chk_limits_"))
async def open_check_limits(call: CallbackQuery):
    code = call.data.replace("chk_limits_", "")
    chk = await db_get_check(code)
    if not chk or chk["creator_id"] != call.from_user.id or chk["status"] != "active":
        return await call.answer("Чек недоступен.", show_alert=True)

    is_multi = (chk["check_type"] == "multi")

    target_str = "Нет"
    if chk["target_username"]:
        target_str = f"@{chk['target_username']}"
    elif chk["target_user_id"]:
        target_str = f"id:{chk['target_user_id']}"
    prem_str = "✅ Вкл" if chk["only_premium"] else "❌ Выкл"
    to_str = f"{chk['min_turnover']:.2f} $" if chk["min_turnover"] > 0 else "Нет"
    dep_str = f"{chk['min_deposits_count']} шт." if chk["min_deposits_count"] > 0 else "Нет"

    kb_rows = []

    if not is_multi:
        kb_rows.append([InlineKeyboardButton(
            text=f"👤 Пользователь: {target_str}",
            callback_data=f"chk_set_user_{code}", style="primary"
        )])

    kb_rows.append([InlineKeyboardButton(
        text=f"⭐ Премиум: {prem_str}",
        callback_data=f"chk_tgl_prem_{code}", style="primary"
    )])
    kb_rows.append([InlineKeyboardButton(
        text=f"🔄 Оборот: {to_str}",
        callback_data=f"chk_set_to_{code}", style="primary"
    )])
    kb_rows.append([InlineKeyboardButton(
        text=f"📥 Депозитов: {dep_str}",
        callback_data=f"chk_set_dep_{code}", style="primary"
    )])
    kb_rows.append([InlineKeyboardButton(
        text="Назад к чеку",
        callback_data=f"chk_view_{code}", style="danger", icon_custom_emoji_id=ICON_IDS["cross"]
    )])

    lines = [
        f"⚙️ <b>Ограничения чека</b>\n",
        "<blockquote>"
    ]
    if not is_multi:
        lines.append(f"• Закреплён за: <b>{target_str}</b>")
    lines.append(f"• Premium: <b>{prem_str}</b>")
    lines.append(f"• Оборот: <b>{to_str}</b>")
    lines.append(f"• Депозитов: <b>{dep_str}</b>")
    if is_multi:
        lines.append("\n<i>💡 Мультичек нельзя привязать к одному пользователю.</i>")
    lines.append("</blockquote>")

    await safe_edit(call, "\n".join(lines), InlineKeyboardMarkup(inline_keyboard=kb_rows))


@checks_router.callback_query(F.data.startswith("chk_tgl_prem_"))
async def toggle_check_prem(call: CallbackQuery):
    code = call.data.replace("chk_tgl_prem_", "")
    chk = await db_get_check(code)
    new_v = 0 if chk["only_premium"] else 1
    await db_update_check_limit(code, "only_premium", new_v)
    await call.answer(f"Премиум: {'Вкл' if new_v else 'Выкл'}")
    await open_check_limits(call)


@checks_router.callback_query(F.data.startswith("chk_set_user_"))
async def ask_check_target(call: CallbackQuery, state: FSMContext):
    code = call.data.replace("chk_set_user_", "")
    chk = await db_get_check(code)
    if not chk or chk["creator_id"] != call.from_user.id:
        return await call.answer("❌ Чек не найден.", show_alert=True)
    if chk["check_type"] == "multi":
        return await call.answer("❌ Мультичек нельзя привязать к пользователю.", show_alert=True)

    await state.update_data(target_chk_id=code)
    await state.set_state(CheckStates.waiting_for_user_target)
    await safe_edit(call,
        "👤 <b>Закрепить за пользователем</b>\n\n<blockquote>@username или ID:</blockquote>",
        InlineKeyboardMarkup(inline_keyboard=[])
    )


@checks_router.message(CheckStates.waiting_for_user_target)
async def save_check_target(message: Message, state: FSMContext):
    data = await state.get_data()
    code = data["target_chk_id"]
    await state.clear()
    txt = message.text.strip().replace("@", "")
    if txt.isdigit():
        await db_update_check_limit(code, "target_user_id", int(txt))
        await db_update_check_limit(code, "target_username", "")
    else:
        await db_update_check_limit(code, "target_username", txt)
        await db_update_check_limit(code, "target_user_id", 0)
    await message.reply(f"✅ Чек прикреплён к: @{txt}")


@checks_router.callback_query(F.data.startswith("chk_set_to_"))
async def ask_check_to(call: CallbackQuery, state: FSMContext):
    code = call.data.replace("chk_set_to_", "")
    await state.update_data(target_chk_id=code)
    await state.set_state(CheckStates.waiting_for_turnover)
    await safe_edit(call, "🔄 Мин. оборот в $:", InlineKeyboardMarkup(inline_keyboard=[]))


@checks_router.message(CheckStates.waiting_for_turnover)
async def save_check_to(message: Message, state: FSMContext):
    data = await state.get_data()
    code = data["target_chk_id"]
    await state.clear()
    try:
        val = float(message.text.replace("$", "").replace(",", ".").strip())
        if math.isnan(val) or math.isinf(val):
            return await message.reply("❌ Некорректное число.")
        await db_update_check_limit(code, "min_turnover", max(0.0, val))
        await message.reply(f"✅ Оборот: {val:.2f} $")
    except ValueError:
        await message.reply("❌ Число:")


@checks_router.callback_query(F.data.startswith("chk_set_dep_"))
async def ask_check_dep(call: CallbackQuery, state: FSMContext):
    code = call.data.replace("chk_set_dep_", "")
    await state.update_data(target_chk_id=code)
    await state.set_state(CheckStates.waiting_for_deposits_count)
    await safe_edit(call, "📥 Мин. кол-во депозитов:", InlineKeyboardMarkup(inline_keyboard=[]))


@checks_router.message(CheckStates.waiting_for_deposits_count)
async def save_check_dep(message: Message, state: FSMContext):
    data = await state.get_data()
    code = data["target_chk_id"]
    await state.clear()
    try:
        val = int(message.text.strip())
        await db_update_check_limit(code, "min_deposits_count", max(0, val))
        await message.reply(f"✅ Депозитов: {val} шт.")
    except ValueError:
        await message.reply("❌ Целое число:")


@checks_router.callback_query(F.data.startswith("chk_view_"))
async def render_existing_check(call: CallbackQuery):
    code = call.data.replace("chk_view_", "")
    chk = await db_get_check(code)
    if not chk:
        return await call.answer("Чек не найден.")
    bot_info = await call.bot.get_me()
    check_url = f"t.me/{bot_info.username}?start=check_{code}"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Отправить", switch_inline_query=f"check_{code}", style="primary")],
        [InlineKeyboardButton(text="Ограничение", callback_data=f"chk_limits_{code}", style="primary")],
        [InlineKeyboardButton(text="Удалить", callback_data=f"chk_delete_{code}", style="danger")],
        [InlineKeyboardButton(text="⬅️ Мои чеки", callback_data="chk_my_list", style="danger", icon_custom_emoji_id=ICON_IDS["cross"])]
    ])
    text = (
        f"😃 <b>Чек</b>\n\n<blockquote>Сумма: <b>{chk['amount_per_activation']:.2f} 💰</b> "
        f"(Осталось: {chk['activations_left']}/{chk['activations_total']})\n\n"
        f"Ссылка:\n<code>{check_url}</code></blockquote>"
    )
    await safe_edit(call, text, kb)


@checks_router.callback_query(F.data.startswith("chk_delete_"))
async def delete_and_refund_check(call: CallbackQuery):
    code = call.data.replace("chk_delete_", "")
    refunded = await db_cancel_check(code, call.from_user.id)
    if refunded > 0:
        await call.answer(f"✅ Удалён! Возврат: +{refunded:.2f} $", show_alert=True)
    else:
        await call.answer("❌ Уже активирован или отменён.", show_alert=True)
    await show_checks_menu(call)


@checks_router.callback_query(F.data == "chk_my_list")
async def show_user_checks(call: CallbackQuery):
    checks = await db_get_user_checks(call.from_user.id)
    if not checks:
        return await call.answer("Нет активных чеков.", show_alert=True)
    kb = []
    for c in checks[:8]:
        kb.append([InlineKeyboardButton(
            text=f"💵 {c['amount_per_activation']:.2f}$ ({c['activations_left']} акт.)",
            callback_data=f"chk_view_{c['check_id']}", style="primary"
        )])
    kb.append([InlineKeyboardButton(text="Назад", callback_data="open_checks_menu", style="danger", icon_custom_emoji_id=ICON_IDS["cross"])])
    await safe_edit(call, "📋 <b>Ваши активные чеки:</b>", InlineKeyboardMarkup(inline_keyboard=kb))