# ============================================================================
# main.py — ВСЁ В ОДНОМ ФАЙЛЕ (со всеми исправлениями)
# ============================================================================
import asyncio
import json
import math
import secrets
import hashlib
import logging
import time
import aiosqlite
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, Router, F, BaseMiddleware
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    InlineQuery, InlineQueryResultArticle, InputTextMessageContent,
    TelegramObject, FSInputFile, Update, BotCommand, BotCommandScopeDefault
)

# ============================================================================
# CONFIG
# ============================================================================
BOT_TOKEN = "8578922515:AAHww7vkF_9xYkw9qNQ6-rT1rQD4pQFoNlw"
oADMIN_IDS = [7966949924]
REF_PERCENT = 0.05

DEFAULT_CHANNEL = "@nc_bet"
DEFAULT_CHAT = "https://t.me/ncbet_chat"
SUPPORT_USERNAME = "theid777"

CRYPTO_PAY_TOKEN = "619106:AAZYp2LZ5cULtRGsXFUJednGEVvpCf4qngZ"
CRYPTO_PAY_NET = "mainnet"
CRYPTO_BASE_URL = (
    "https://pay.crypt.bot/api" if CRYPTO_PAY_NET == "mainnet"
    else "https://testnet-pay.crypt.bot/api"
)

EMOJI = {
    "mine": '<tg-emoji emoji-id="5801074131839487552">💣</tg-emoji>',
    "gem": '<tg-emoji emoji-id="5377383515123912286">💎</tg-emoji>',
    "star": '<tg-emoji emoji-id="5958376256788502078">⭐️</tg-emoji>',
    "cash": '<tg-emoji emoji-id="5433770199427883814">💵</tg-emoji>',
    "fire": '<tg-emoji emoji-id="5289722755871162900">🔥</tg-emoji>',
    "trophy": '<tg-emoji emoji-id="5188344996356448758">🏆</tg-emoji>',
    "shield": '<tg-emoji emoji-id="5972226216353074147">🛡</tg-emoji>',
    "cross": '<tg-emoji emoji-id="6046150802609804972">❌</tg-emoji>',
    "check": '<tg-emoji emoji-id="5776375003280838798">✅</tg-emoji>',
    "rocket": '<tg-emoji emoji-id="5372917041193828849">🚀</tg-emoji>',
    "tower": '🗼',
    "sport": '⚽'
}

TOP_NUMBERS = {
    1: '<tg-emoji emoji-id="5303184424622376167">1️⃣</tg-emoji>',
    2: '<tg-emoji emoji-id="5303549840439920368">2️⃣</tg-emoji>',
    3: '<tg-emoji emoji-id="5303433253552669683">3️⃣</tg-emoji>',
    4: '<tg-emoji emoji-id="5305407254881650239">4️⃣</tg-emoji>',
    5: '<tg-emoji emoji-id="5305536533397261544">5️⃣</tg-emoji>',
    6: '<tg-emoji emoji-id="5305270984159284390">6️⃣</tg-emoji>',
    7: '<tg-emoji emoji-id="5303243025156163408">7️⃣</tg-emoji>',
    8: '<tg-emoji emoji-id="5305696563878709468">8️⃣</tg-emoji>',
    9: '<tg-emoji emoji-id="5305412541986392129">9️⃣</tg-emoji>',
    10: '<tg-emoji emoji-id="5303228851764090729">🔟</tg-emoji>'
}

ICON_IDS = {
    "mine": "5801074131839487552",
    "gem": "5377383515123912286",
    "star": "5958376256788502078",
    "cash": "5433770199427883814",
    "fire": "5289722755871162900",
    "trophy": "5188344996356448758",
    "shield": "5972226216353074147",
    "cross": "6046150802609804972",
    "check": "5776375003280838798",
    "rocket": "5372917041193828849"
}

# ============================================================================
# DATABASE
# ============================================================================
DB_PATH = "casino.db"
EXCLUDED_USER_IDS = (7966949924,)
EXCLUDED_USERNAMES = ("theid777",)
EXCLUDED_CHAT_IDS = (-1004294553882,)


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            display_mode TEXT DEFAULT 'first_name',
            custom_nick TEXT,
            balance REAL DEFAULT 0.0,
            ref_balance REAL DEFAULT 0.0,
            referrer_id INTEGER DEFAULT 0,
            turnover REAL DEFAULT 0.0,
            deposits_count INTEGER DEFAULT 0,
            deposits_sum REAL DEFAULT 0.0,
            withdrawals_sum REAL DEFAULT 0.0,
            is_banned INTEGER DEFAULT 0,
            ban_games INTEGER DEFAULT 0,
            ban_deposits INTEGER DEFAULT 0,
            ban_withdraws INTEGER DEFAULT 0,
            has_premium INTEGER DEFAULT 0,
            selected_bet REAL DEFAULT 0.05,
            selected_mines INTEGER DEFAULT 3,
            selected_traps INTEGER DEFAULT 1,
            user_rank TEXT DEFAULT 'None',
            cashback_balance REAL DEFAULT 0.0,
            cashback_total REAL DEFAULT 0.0,
            reg_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            wager_required REAL DEFAULT 0.0,
            wager_completed REAL DEFAULT 0.0
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS chat_jackpots (
            chat_id INTEGER PRIMARY KEY,
            chat_title TEXT,
            jackpot_balance REAL DEFAULT 0.0,
            turnover REAL DEFAULT 0.0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS bot_checks (
            check_id TEXT PRIMARY KEY,
            creator_id INTEGER,
            check_type TEXT,
            amount_per_activation REAL,
            total_amount REAL,
            activations_total INTEGER DEFAULT 1,
            activations_left INTEGER DEFAULT 1,
            target_user_id INTEGER DEFAULT 0,
            target_username TEXT DEFAULT '',
            min_turnover REAL DEFAULT 0.0,
            min_deposits_count INTEGER DEFAULT 0,
            only_premium INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS check_activations (
            check_id TEXT,
            user_id INTEGER,
            amount REAL,
            activated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(check_id, user_id)
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS game_sessions (
            user_id INTEGER PRIMARY KEY,
            game_type TEXT,
            data TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS games_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            game_name TEXT,
            bet REAL,
            payout REAL,
            win INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            type TEXT,
            amount REAL,
            gateway TEXT,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            invoice_id TEXT PRIMARY KEY,
            user_id INTEGER,
            amount REAL,
            gateway TEXT DEFAULT 'cryptobot',
            status TEXT DEFAULT 'active',
            bonus_type TEXT DEFAULT 'normal',
            bonus_amount REAL DEFAULT 0.0,
            wager_required REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS withdraw_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            gateway TEXT DEFAULT 'cryptobot',
            wallet TEXT DEFAULT '',
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS promos (
            code TEXT PRIMARY KEY,
            reward REAL,
            activations_left INTEGER,
            min_turnover REAL DEFAULT 0,
            min_deposits_sum REAL DEFAULT 0,
            min_withdraws_sum REAL DEFAULT 0,
            only_premium INTEGER DEFAULT 0
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS promo_activations (
            code TEXT,
            user_id INTEGER,
            activated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(code, user_id)
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS sport_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team1 TEXT NOT NULL,
            team2 TEXT NOT NULL,
            coef1 REAL NOT NULL,
            coef2 REAL NOT NULL,
            description TEXT DEFAULT '',
            ai_prediction TEXT DEFAULT '',
            lineups TEXT DEFAULT '',
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS sport_bets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            event_id INTEGER NOT NULL,
            bet_on TEXT NOT NULL,
            amount REAL NOT NULL,
            coef REAL NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        migrations = [
            "ALTER TABLE chat_jackpots ADD COLUMN turnover REAL DEFAULT 0.0",
            "ALTER TABLE users ADD COLUMN user_rank TEXT DEFAULT 'None'",
            "ALTER TABLE users ADD COLUMN cashback_balance REAL DEFAULT 0.0",
            "ALTER TABLE users ADD COLUMN cashback_total REAL DEFAULT 0.0",
            "ALTER TABLE users ADD COLUMN has_premium INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN wager_required REAL DEFAULT 0.0",
            "ALTER TABLE users ADD COLUMN wager_completed REAL DEFAULT 0.0"
        ]
        for mig in migrations:
            try:
                await db.execute(mig)
                await db.commit()
            except Exception:
                pass

        await db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('channel_link', '@nc_bet')")
        await db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('chat_link', 'https://t.me/ncbet_chat')")
        await db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('withdraw_mode', 'manual')")
        await db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('gateway_cryptobot', '1')")
        await db.commit()


async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cur:
            user = await cur.fetchone()
            if user:
                return user
        await register_user(user_id, "")
        async with aiosqlite.connect(DB_PATH) as db2:
            db2.row_factory = aiosqlite.Row
            async with db2.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cur2:
                return await cur2.fetchone()


async def get_all_user_ids():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users WHERE is_banned = 0") as cur:
            rows = await cur.fetchall()
            return [r[0] for r in rows]


async def register_user(user_id: int, username: str, referrer_id: int = 0, has_premium: int = 0):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT user_id, referrer_id FROM users WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
        if not row:
            final_ref = referrer_id if referrer_id and referrer_id != user_id else 0
            await db.execute("""
            INSERT INTO users (user_id, username, referrer_id, has_premium, selected_bet, user_rank, wager_required, wager_completed)
            VALUES (?, ?, ?, ?, 0.05, 'None', 0.0, 0.0)
            """, (user_id, username, final_ref, has_premium))
            await db.commit()
        elif row["referrer_id"] == 0 and referrer_id and referrer_id != user_id:
            await db.execute("UPDATE users SET referrer_id = ? WHERE user_id = ?", (referrer_id, user_id))
            await db.commit()


async def update_balance(user_id: int, delta: float):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET balance = ROUND(balance + ?, 4) WHERE user_id = ?", (delta, user_id))
        await db.commit()


async def add_turnover(user_id: int, amount: float):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT turnover, user_rank, balance FROM users WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
        if not row:
            return
        old_to = row["turnover"]
        new_to = round(old_to + amount, 4)
        current_rank = row["user_rank"] or "None"
        new_rank = current_rank
        reward_bonus = 0.0
        if new_to >= 100000 and current_rank != "Gold":
            new_rank = "Gold"
            if current_rank not in ["Silver", "Gold"]:
                reward_bonus = 60.0
        elif new_to >= 50000 and current_rank not in ["Silver", "Gold"]:
            new_rank = "Silver"
            if current_rank != "Bronze":
                reward_bonus = 30.0
        elif new_to >= 10000 and current_rank == "None":
            new_rank = "Bronze"
            reward_bonus = 15.0
        await db.execute("""
        UPDATE users SET turnover = ?, user_rank = ?, balance = ROUND(balance + ?, 4) WHERE user_id = ?
        """, (new_to, new_rank, reward_bonus, user_id))
        await db.commit()


async def set_user_setting(user_id: int, field: str, value):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE users SET {field} = ? WHERE user_id = ?", (value, user_id))
        await db.commit()


async def get_referrals_count(user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users WHERE referrer_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0


async def claim_referral_balance(user_id: int) -> float:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT ref_balance FROM users WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
        if not row or row["ref_balance"] <= 0:
            return 0.0
        amount = row["ref_balance"]
        await db.execute("UPDATE users SET balance = ROUND(balance + ?, 4), ref_balance = 0.0 WHERE user_id = ?", (amount, user_id))
        await db.execute("INSERT INTO transactions (user_id, type, amount, gateway, status) VALUES (?, 'ref_claim', ?, 'internal', 'success')", (user_id, amount))
        await db.commit()
        return amount


async def transfer_balance(from_uid: int, to_uid: int, amount: float) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT balance FROM users WHERE user_id = ?", (from_uid,)) as cur:
            sender = await cur.fetchone()
        if not sender or sender["balance"] < amount:
            return False
        await db.execute("UPDATE users SET balance = ROUND(balance - ?, 4) WHERE user_id = ?", (amount, from_uid))
        await db.execute("UPDATE users SET balance = ROUND(balance + ?, 4) WHERE user_id = ?", (amount, to_uid))
        await db.execute("INSERT INTO transactions (user_id, type, amount, gateway, status) VALUES (?, 'transfer_out', ?, 'chat', 'success')", (from_uid, amount))
        await db.execute("INSERT INTO transactions (user_id, type, amount, gateway, status) VALUES (?, 'transfer_in', ?, 'chat', 'success')", (to_uid, amount))
        await db.commit()
        return True


# --- CHAT JACKPOT ---
async def get_chat_jackpot(chat_id: int, chat_title: str) -> float:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        INSERT INTO chat_jackpots (chat_id, chat_title, jackpot_balance, turnover)
        VALUES (?, ?, 0.0, 0.0)
        ON CONFLICT(chat_id) DO UPDATE SET chat_title = excluded.chat_title
        """, (chat_id, chat_title))
        await db.commit()
        async with db.execute("SELECT jackpot_balance FROM chat_jackpots WHERE chat_id = ?", (chat_id,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0.0


async def add_chat_jackpot(chat_id: int, chat_title: str, amount: float):
    pool_bonus = round(amount * 0.005, 4)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        INSERT INTO chat_jackpots (chat_id, chat_title, jackpot_balance, turnover)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(chat_id) DO UPDATE SET 
            jackpot_balance = ROUND(jackpot_balance + ?, 4),
            turnover = ROUND(turnover + ?, 4),
            chat_title = excluded.chat_title,
            updated_at = CURRENT_TIMESTAMP
        """, (chat_id, chat_title, pool_bonus, amount, pool_bonus, amount))
        await db.commit()


async def add_chat_turnover_only(chat_id: int, chat_title: str, amount: float):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        INSERT INTO chat_jackpots (chat_id, chat_title, jackpot_balance, turnover)
        VALUES (?, ?, 0.0, ?)
        ON CONFLICT(chat_id) DO UPDATE SET 
            turnover = ROUND(turnover + ?, 4),
            chat_title = excluded.chat_title,
            updated_at = CURRENT_TIMESTAMP
        """, (chat_id, chat_title, amount, amount))
        await db.commit()


async def claim_chat_jackpot(chat_id: int, owner_id: int) -> float:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT jackpot_balance FROM chat_jackpots WHERE chat_id = ?", (chat_id,)) as cur:
            row = await cur.fetchone()
        if not row or row["jackpot_balance"] < 0.50:
            return 0.0
        amount = row["jackpot_balance"]
        await db.execute("UPDATE chat_jackpots SET jackpot_balance = 0.0 WHERE chat_id = ?", (chat_id,))
        await db.execute("UPDATE users SET balance = ROUND(balance + ?, 4) WHERE user_id = ?", (amount, owner_id))
        await db.execute("INSERT INTO transactions (user_id, type, amount, gateway, status) VALUES (?, 'jackpot_claim', ?, 'chat_pool', 'success')", (owner_id, amount))
        await db.commit()
        return amount


# --- TOPS ---
async def get_top_players(category: str, limit: int = 10):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        user_ids_str = ",".join(map(str, EXCLUDED_USER_IDS))
        exclude_u = f"AND u.user_id NOT IN ({user_ids_str}) AND LOWER(COALESCE(u.username, '')) NOT IN ('theid777')"
        if category == "turnover":
            q = f"SELECT u.user_id, u.username, u.turnover as val FROM users u WHERE 1=1 {exclude_u} ORDER BY u.turnover DESC LIMIT ?"
            async with db.execute(q, (limit,)) as cur:
                return await cur.fetchall()
        elif category == "balance":
            q = f"SELECT u.user_id, u.username, u.balance as val FROM users u WHERE 1=1 {exclude_u} ORDER BY u.balance DESC LIMIT ?"
            async with db.execute(q, (limit,)) as cur:
                return await cur.fetchall()
        elif category == "referrals":
            q = f"""SELECT u.user_id, u.username, COUNT(r.user_id) as val 
                    FROM users u LEFT JOIN users r ON r.referrer_id = u.user_id
                    WHERE 1=1 {exclude_u} GROUP BY u.user_id ORDER BY val DESC LIMIT ?"""
            async with db.execute(q, (limit,)) as cur:
                return await cur.fetchall()
        elif category == "chats":
            chat_ids_str = ",".join(map(str, EXCLUDED_CHAT_IDS))
            q = f"""SELECT chat_id, chat_title, COALESCE(turnover, 0.0) as val 
                    FROM chat_jackpots WHERE chat_id NOT IN ({chat_ids_str}) ORDER BY val DESC LIMIT ?"""
            async with db.execute(q, (limit,)) as cur:
                return await cur.fetchall()
        return []


async def reset_top_statistics():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET turnover = 0.0")
        await db.execute("UPDATE chat_jackpots SET turnover = 0.0")
        await db.commit()


async def create_promo_code(code, reward, activations, min_turnover=0.0, min_deposits_sum=0.0, only_premium=0) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute("""
            INSERT INTO promos (code, reward, activations_left, min_turnover, min_deposits_sum, only_premium)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (code.strip().upper(), round(reward, 2), int(activations), round(min_turnover, 2), round(min_deposits_sum, 2), int(only_premium)))
            await db.commit()
            return True
        except Exception:
            return False


# --- SESSIONS ---
async def db_save_session(user_id: int, game_type: str, data: dict):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        INSERT OR REPLACE INTO game_sessions (user_id, game_type, data, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (user_id, game_type, json.dumps(data)))
        await db.commit()


async def db_get_session(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM game_sessions WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
        return {"game_type": row["game_type"], "data": json.loads(row["data"])} if row else None


async def db_delete_session(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM game_sessions WHERE user_id = ?", (user_id,))
        await db.commit()


async def db_cancel_active_session(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT game_type FROM game_sessions WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
        if not row:
            return False
        await db.execute("DELETE FROM game_sessions WHERE user_id = ?", (user_id,))
        await db.commit()
        return True


async def record_game(user_id: int, game_name: str, bet: float, payout: float, win: bool, chat_id: int = 0, chat_title: str = ""):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        INSERT INTO games_history (user_id, game_name, bet, payout, win) VALUES (?, ?, ?, ?, ?)
        """, (user_id, game_name, bet, payout, 1 if win else 0))
        if not win:
            await db.execute("""
            UPDATE users SET wager_required = ROUND(MAX(0, wager_required - ?), 4),
                             wager_completed = ROUND(wager_completed + ?, 4)
            WHERE user_id = ?
            """, (bet, bet, user_id))
            async with db.execute("SELECT referrer_id FROM users WHERE user_id = ?", (user_id,)) as cur:
                row = await cur.fetchone()
            if row and row[0] != 0:
                ref_id = row[0]
                reward = round(bet * 0.05, 4)
                await db.execute("""
                UPDATE users SET balance = ROUND(balance + ?, 4), ref_balance = ROUND(ref_balance + ?, 4) WHERE user_id = ?
                """, (reward, reward, ref_id))
        await db.commit()
    if chat_id != 0:
        if not win:
            await add_chat_jackpot(chat_id, chat_title, bet)
        else:
            await add_chat_turnover_only(chat_id, chat_title, bet)


async def get_history(user_id: int, days: int = 7):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cutoff = datetime.utcnow() - timedelta(days=days)
        async with db.execute("""
        SELECT game_name, bet, payout, win, created_at FROM games_history
        WHERE user_id = ? AND created_at >= ? ORDER BY id DESC LIMIT 15
        """, (user_id, cutoff)) as cur:
            return await cur.fetchall()


async def get_transactions(user_id: int, limit: int = 10):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
        SELECT type, amount, gateway, status, created_at FROM transactions
        WHERE user_id = ? ORDER BY id DESC LIMIT ?
        """, (user_id, limit)) as cur:
            return await cur.fetchall()


async def get_setting(key: str, default: str = ""):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM settings WHERE key = ?", (key,)) as cur:
            res = await cur.fetchone()
            return res[0] if res else default


async def set_setting(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
        await db.commit()


# --- CHECKS DB ---
async def db_create_check(check_id, creator_id, check_type, amount_per_act, activations) -> bool:
    total = round(amount_per_act * activations, 2)
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT balance FROM users WHERE user_id = ?", (creator_id,)) as cur:
            user = await cur.fetchone()
        if not user or user["balance"] < total:
            return False
        await db.execute("UPDATE users SET balance = ROUND(balance - ?, 4) WHERE user_id = ?", (total, creator_id))
        await db.execute("""
        INSERT INTO bot_checks (check_id, creator_id, check_type, amount_per_activation, total_amount, activations_total, activations_left)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (check_id, creator_id, check_type, amount_per_act, total, activations, activations))
        await db.commit()
        return True


async def db_get_check(check_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM bot_checks WHERE check_id = ?", (check_id,)) as cur:
            return await cur.fetchone()


async def db_get_user_checks(creator_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM bot_checks WHERE creator_id = ? AND status = 'active' ORDER BY created_at DESC", (creator_id,)) as cur:
            return await cur.fetchall()


async def db_update_check_limit(check_id: str, field: str, value):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE bot_checks SET {field} = ? WHERE check_id = ?", (value, check_id))
        await db.commit()


async def db_cancel_check(check_id: str, creator_id: int) -> float:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM bot_checks WHERE check_id = ? AND creator_id = ? AND status = 'active'", (check_id, creator_id)) as cur:
            chk = await cur.fetchone()
        if not chk:
            return 0.0
        refund_amount = round(chk["amount_per_activation"] * chk["activations_left"], 2)
        await db.execute("UPDATE bot_checks SET status = 'cancelled', activations_left = 0 WHERE check_id = ?", (check_id,))
        if refund_amount > 0:
            await db.execute("UPDATE users SET balance = ROUND(balance + ?, 4) WHERE user_id = ?", (refund_amount, creator_id))
        await db.commit()
        return refund_amount


# === ИСПРАВЛЕННАЯ ФУНКЦИЯ АКТИВАЦИИ ЧЕКА ===
async def db_activate_check(check_id: str, user_id: int, is_premium_user: bool = False):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM bot_checks WHERE check_id = ?", (check_id,)) as cur:
            chk = await cur.fetchone()
        if not chk or chk["status"] != "active" or chk["activations_left"] <= 0:
            return False, "❌ Чек уже закончился или был отменён.", 0.0, 0
        if chk["creator_id"] == user_id:
            return False, "❌ Вы не можете активировать собственный чек.", 0.0, 0
        async with db.execute("SELECT 1 FROM check_activations WHERE check_id = ? AND user_id = ?", (check_id, user_id)) as cur:
            if await cur.fetchone():
                return False, "❌ Вы уже активировали этот чек.", 0.0, 0
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cur:
            user = await cur.fetchone()
        if not user:
            return False, "❌ Ошибка профиля пользователя.", 0.0, 0
        if user["is_banned"]:
            return False, "⛔ Вы заблокированы.", 0.0, 0

        # === СТРОГАЯ ПРОВЕРКА ПРИВЯЗКИ (главный фикс!) ===
        target_uid = chk["target_user_id"] or 0
        target_uname = (chk["target_username"] or "").strip().lower()
        user_uname = (user["username"] or "").strip().lower()

        if target_uid != 0:
            # Чек привязан к конкретному ID — только он может активировать
            if target_uid != user_id:
                return False, "🔒 Этот чек закреплён за другим пользователем.", 0.0, 0
        elif target_uname:
            # Чек привязан к username — если у юзера нет username или он не совпал → отказ
            if not user_uname or user_uname != target_uname:
                return False, f"🔒 Чек предназначен только для @{chk['target_username']}.", 0.0, 0

        # === СТРОГАЯ ПРОВЕРКА PREMIUM (защита от None) ===
        if int(chk["only_premium"] or 0) == 1 and not bool(is_premium_user):
            return False, "⭐ Для активации чека требуется Telegram Premium.", 0.0, 0        if user["turnover"] < chk["min_turnover"]:
            return False, f"❌ Требуется оборот: {chk['min_turnover']:.2f} $ (у вас {user['turnover']:.2f} $)", 0.0, 0
        if user["deposits_count"] < chk["min_deposits_count"]:
            return False, f"❌ Требуется депозитов: {chk['min_deposits_count']} шт.", 0.0, 0

        amount = chk["amount_per_activation"]
        new_left = chk["activations_left"] - 1
        new_status = "completed" if new_left == 0 else "active"
        await db.execute("UPDATE bot_checks SET activations_left = ?, status = ? WHERE check_id = ?", (new_left, new_status, check_id))
        await db.execute("INSERT INTO check_activations (check_id, user_id, amount) VALUES (?, ?, ?)", (check_id, user_id, amount))
        await db.execute("UPDATE users SET balance = ROUND(balance + ?, 4) WHERE user_id = ?", (amount, user_id))
        await db.execute("INSERT INTO transactions (user_id, type, amount, gateway, status) VALUES (?, 'check_in', ?, 'check', 'success')", (user_id, amount))
        await db.commit()
        return True, f"✅ Чек активирован на +{amount:.2f} $!", amount, chk["creator_id"]


# --- SPORT DB ---
async def db_add_sport_event(team1, team2, coef1, coef2, description="", ai_prediction="", lineups=""):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
        INSERT INTO sport_events (team1, team2, coef1, coef2, description, ai_prediction, lineups)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (team1, team2, coef1, coef2, description, ai_prediction, lineups))
        await db.commit()
        return cur.lastrowid


async def db_get_active_sport_events():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM sport_events WHERE is_active = 1 ORDER BY id DESC") as cur:
            return await cur.fetchall()


async def db_get_sport_event(event_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM sport_events WHERE id = ?", (event_id,)) as cur:
            return await cur.fetchone()


async def db_deactivate_sport_event(event_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE sport_events SET is_active = 0 WHERE id = ?", (event_id,))
        await db.commit()


async def db_place_sport_bet(user_id: int, event_id: int, bet_on: str, amount: float, coef: float) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)) as cur:
            user = await cur.fetchone()
        if not user or user["balance"] < amount:
            return -1
        await db.execute("UPDATE users SET balance = ROUND(balance - ?, 4) WHERE user_id = ?", (amount, user_id))
        cur = await db.execute("""
        INSERT INTO sport_bets (user_id, event_id, bet_on, amount, coef, status) VALUES (?, ?, ?, ?, ?, 'pending')
        """, (user_id, event_id, bet_on, amount, coef))
        await db.execute("INSERT INTO transactions (user_id, type, amount, gateway, status) VALUES (?, 'sport_bet', ?, 'sport', 'success')", (user_id, amount))
        await db.commit()
        return cur.lastrowid


async def db_get_pending_sport_bets():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
        SELECT sb.*, se.team1, se.team2, se.coef1, se.coef2
        FROM sport_bets sb JOIN sport_events se ON sb.event_id = se.id
        WHERE sb.status = 'pending' ORDER BY sb.id DESC
        """) as cur:
            return await cur.fetchall()


async def db_resolve_sport_bet(bet_id: int, won: bool) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM sport_bets WHERE id = ?", (bet_id,)) as cur:
            bet = await cur.fetchone()
        if not bet or bet["status"] != "pending":
            return {}
        if won:
            payout = round(bet["amount"] * bet["coef"], 2)
            await db.execute("UPDATE users SET balance = ROUND(balance + ?, 4) WHERE user_id = ?", (payout, bet["user_id"]))
            await db.execute("UPDATE sport_bets SET status = 'won' WHERE id = ?", (bet_id,))
            await db.execute("INSERT INTO transactions (user_id, type, amount, gateway, status) VALUES (?, 'sport_win', ?, 'sport', 'success')", (bet["user_id"], payout))
            result = {"user_id": bet["user_id"], "amount": bet["amount"], "payout": payout, "coef": bet["coef"], "won": True}
        else:
            await db.execute("UPDATE sport_bets SET status = 'lost' WHERE id = ?", (bet_id,))
            result = {"user_id": bet["user_id"], "amount": bet["amount"], "payout": 0.0, "coef": bet["coef"], "won": False}
        await db.commit()
        return result


async def db_get_user_sport_bets(user_id: int, limit: int = 10):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
        SELECT sb.*, se.team1, se.team2 FROM sport_bets sb JOIN sport_events se ON sb.event_id = se.id
        WHERE sb.user_id = ? ORDER BY sb.id DESC LIMIT ?
        """, (user_id, limit)) as cur:
            return await cur.fetchall()


# ============================================================================
# CRYPTOPAY API
# ============================================================================
import aiohttp


async def cb_create_invoice(amount: float, user_id: int):
    if not CRYPTO_PAY_TOKEN or amount < 0.05:
        return None
    url = f"{CRYPTO_BASE_URL}/createInvoice"
    headers = {"Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN}
    payload = {"asset": "USDT", "amount": f"{amount:.2f}", "description": f"Пополнение #{user_id}", "payload": str(user_id)}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers, timeout=10) as resp:
                data = await resp.json()
                if data.get("ok"):
                    return data.get("result")
                print(f"CryptoBot createInvoice error: {data}")
                return None
    except Exception as e:
        print(f"CryptoBot createInvoice exception: {e}")
        return None


async def cb_check_stat(invoice_id: int):
    if not CRYPTO_PAY_TOKEN:
        return None
    url = f"{CRYPTO_BASE_URL}/getInvoices"
    headers = {"Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN}
    params = {"invoice_ids": str(invoice_id)}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers, timeout=10) as resp:
                data = await resp.json()
                if data.get("ok") and data["result"]["items"]:
                    return data["result"]["items"][0]["status"]
                return None
    except Exception as e:
        print(f"CryptoBot checkInvoice exception: {e}")
        return None


async def cb_create_check(amount: float):
    if not CRYPTO_PAY_TOKEN:
        return None
    if amount < 0.10:
        return None
    url = f"{CRYPTO_BASE_URL}/createCheck"
    headers = {"Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN}
    payload = {"asset": "USDT", "amount": f"{amount:.2f}"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers, timeout=15) as resp:
                data = await resp.json()
                if data.get("ok"):
                    result = data.get("result")
                    if result and result.get("bot_check_url"):
                        return result
                return None
    except Exception as e:
        print(f"CryptoBot createCheck exception: {e}")
        return None


# ============================================================================
# MIDDLEWARES
# ============================================================================
class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, slowmode_seconds: float = 1):
        self.slowmode = slowmode_seconds
        self.users_last_action: dict = {}

    async def __call__(self, handler, event, data):
        user_id = None
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery) and event.from_user:
            user_id = event.from_user.id
        if user_id:
            u = await get_user(user_id)
            if u and u["is_banned"]:
                if isinstance(event, CallbackQuery):
                    await event.answer("⛔ Вы заблокированы в системе.", show_alert=True)
                return
            now = time.time()
            last_action = self.users_last_action.get(user_id, 0.0)
            elapsed = now - last_action
            is_game_click = False
            if isinstance(event, CallbackQuery) and event.data:
                if event.data.startswith("m_clk_") or event.data.startswith("t_clk_"):
                    is_game_click = True
            if not is_game_click and elapsed < self.slowmode:
                time_left = round(self.slowmode - elapsed, 1)
                warning = f"⏳ Задержка! Подождите {time_left} сек."
                if isinstance(event, CallbackQuery):
                    await event.answer(warning, show_alert=True)
                elif isinstance(event, Message):
                    await event.reply(f"<blockquote>{warning}</blockquote>", parse_mode="HTML")
                return
            self.users_last_action[user_id] = now
        return await handler(event, data)


# ============================================================================
# ROUTERS
# ============================================================================
admin_router = Router()
admin_sport_router = Router()
finance_router = Router()
checks_router = Router()
games_router = Router()
dice_router = Router()
sport_router = Router()
chat_router = Router()
quick_router = Router()
user_router = Router()

USER_LOCKS: dict = {}


def get_lock(uid: int) -> asyncio.Lock:
    if uid not in USER_LOCKS:
        USER_LOCKS[uid] = asyncio.Lock()
    return USER_LOCKS[uid]


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def is_chat_group(msg: Message) -> bool:
    return msg.chat.type in ["group", "supergroup"]


async def safe_edit(call: CallbackQuery, text: str, kb: InlineKeyboardMarkup):
    try:
        await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        try:
            await call.message.delete()
        except Exception:
            pass
        try:
            await call.message.answer(text, reply_markup=kb, parse_mode="HTML")
        except Exception as e:
            print(f"safe_edit fail: {e}")


# ============================================================================
# KEYBOARDS
# ============================================================================
def main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Играть", callback_data="open_games", style="success", icon_custom_emoji_id=ICON_IDS["fire"]),
            InlineKeyboardButton(text="Игровые чаты", callback_data="open_chats", style="primary")
        ],
        [
            InlineKeyboardButton(text="Профиль", callback_data="profile", style="primary", icon_custom_emoji_id=ICON_IDS["rocket"]),
            InlineKeyboardButton(text="Реф Программа", callback_data="referrals", style="primary", icon_custom_emoji_id=ICON_IDS["cash"])
        ],
        [
            InlineKeyboardButton(text="Кешбэк", callback_data="open_cashback", style="success", icon_custom_emoji_id=ICON_IDS["cash"]),
            InlineKeyboardButton(text="Топ игроков", callback_data="open_top", style="primary", icon_custom_emoji_id=ICON_IDS["trophy"])
        ],
        [InlineKeyboardButton(text="Правила", callback_data="rules", icon_custom_emoji_id=ICON_IDS["shield"])]
    ])


def games_select_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Кости", callback_data="game_dice", style="primary"),
            InlineKeyboardButton(text="Мины", callback_data="game_mines", style="danger", icon_custom_emoji_id=ICON_IDS["mine"]),
            InlineKeyboardButton(text="Башня", callback_data="game_tower", style="success", icon_custom_emoji_id=ICON_IDS["star"])
        ],
        [InlineKeyboardButton(text="⚽ Ставки на спорт", callback_data="game_sport", style="primary", icon_custom_emoji_id=ICON_IDS["fire"])],
        [InlineKeyboardButton(text="Назад", callback_data="back_to_main", style="danger", icon_custom_emoji_id=ICON_IDS["cross"])]
    ])


# ============================================================================
# USER HANDLERS
# ============================================================================
RANK_CASHBACK_PERCENT = {"None": 0.0, "Bronze": 3.0, "Silver": 6.0, "Gold": 8.0}


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


@user_router.callback_query(F.data == "back_to_main")
async def back_to_main(call: CallbackQuery):
    bot_info = await call.bot.get_me()
    text = f"{EMOJI['star']} <b>Главное меню @{bot_info.username}</b>\n\n<blockquote>Подписывайся на наш канал @nc_bet</blockquote>"
    await safe_edit(call, text, main_kb())


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


@user_router.callback_query(F.data == "open_games")
async def on_open_games(call: CallbackQuery):
    user = await get_user(call.from_user.id)
    try:
        photo = FSInputFile("play.png")
        text = (
            f"🎮 <b>Выбирайте игру!</b>\n\n"
            f"<blockquote>Баланс — <b>{user['balance']:.2f}</b> {EMOJI['cash']}\n"
            f"Ставка — <b>{user['selected_bet']:.2f}</b> {EMOJI['cash']}</blockquote>"
        )
        try:
            await call.message.delete()
        except Exception:
            pass
        await call.message.answer_photo(photo=photo, caption=text, reply_markup=games_select_kb(), parse_mode="HTML")
    except Exception as e:
        print(f"play.png err: {e}")
        text = (
            f"🎮 <b>Выбирайте игру!</b>\n\n"
            f"<blockquote>Баланс — <b>{user['balance']:.2f}</b> {EMOJI['cash']}\n"
            f"Ставка — <b>{user['selected_bet']:.2f}</b> {EMOJI['cash']}</blockquote>"
        )
        await safe_edit(call, text, games_select_kb())


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
    await message.reply(f"🎉 <b>Промокод активирован!</b>\n<blockquote>+{promo['reward']:.2f} $</blockquote>", parse_mode="HTML")


# ============================================================================
# CHAT HANDLERS
# ============================================================================
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
    await safe_edit(call, "\n".join(lines), kb)


# /send — перевод между игроками
@chat_router.message(Command("send"))
async def cmd_chat_send(message: Message):
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


@chat_router.message(F.text.lower().in_(["джекпот", "jackpot", "/jackpot"]))
async def show_chat_jackpot(message: Message):
    if not is_chat_group(message):
        return
    chat_id = message.chat.id
    chat_title = message.chat.title or "Игровой Чат"
    current_jackpot = await get_chat_jackpot(chat_id, chat_title)
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


# ============================================================================
# FINANCE HANDLERS
# ============================================================================
MIN_DEPOSIT = 0.10
MIN_WITHDRAW_USER = 1.00
MIN_WITHDRAW_ADMIN = 0.10
WAGER_PERCENT = 0.10


class FinanceStates(StatesGroup):
    waiting_for_deposit_amount = State()
    waiting_for_withdraw_amount = State()


def dep_gateways_kb(amount: float) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"💰 Обычное ({amount:.2f}$)", callback_data=f"dep_gw_cb_{amount}", style="success", icon_custom_emoji_id=ICON_IDS["cash"])],
        [InlineKeyboardButton(text=f"⚡ x2 БОНУС ({amount*2:.2f}$)", callback_data=f"dep_gw_x2_{amount}", style="danger", icon_custom_emoji_id=ICON_IDS["fire"])],
        [InlineKeyboardButton(text="Отмена", callback_data="back_to_main", style="danger", icon_custom_emoji_id=ICON_IDS["cross"])]
    ])


def withdraw_gateways_kb(amount: float) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏦 CryptoBot Чек", callback_data=f"w_gw_cb_{amount}", style="success", icon_custom_emoji_id=ICON_IDS["cash"])],
        [InlineKeyboardButton(text="Отмена", callback_data="back_to_main", style="danger", icon_custom_emoji_id=ICON_IDS["cross"])]
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
        f"<i>💡 Бонус 10% нужно отыграть перед выводом.</i>\n"
        f"<i>⚡ x2 — удвоенная сумма, отыгрыш x4!</i></blockquote>"
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
        f"📥 <b>Пополнение: {amount:.2f} $</b>\n\n<blockquote>Выберите тип:</blockquote>",
        reply_markup=dep_gateways_kb(amount), parse_mode="HTML"
    )


@finance_router.callback_query(F.data.startswith("dep_gw_cb_"))
async def cb_dep_call(call: CallbackQuery):
    amount = float(call.data.split("_")[3])
    await process_deposit(call, amount, bonus_type="normal")


@finance_router.callback_query(F.data.startswith("dep_gw_x2_"))
async def cb_dep_x2_call(call: CallbackQuery):
    amount = float(call.data.split("_")[3])
    await process_deposit(call, amount, bonus_type="x2")


async def process_deposit(call: CallbackQuery, amount: float, bonus_type: str = "normal"):
    inv = await cb_create_invoice(amount, call.from_user.id)
    if not inv:
        return await call.answer("❌ Ошибка CryptoBot API.", show_alert=True)
    inv_id = str(inv["invoice_id"])
    if bonus_type == "x2":
        bonus_amount = amount
        wager_required = amount * 4
        bonus_text = "⚡ x2 БОНУС"
    else:
        bonus_amount = amount * WAGER_PERCENT
        wager_required = amount * WAGER_PERCENT
        bonus_text = "💰 Обычное"
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO invoices (invoice_id, user_id, amount, gateway, status, bonus_type, bonus_amount, wager_required) VALUES (?, ?, ?, 'cryptobot', 'active', ?, ?, ?)",
            (inv_id, call.from_user.id, amount, bonus_type, bonus_amount, wager_required)
        )
        await db.commit()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить", url=inv["bot_invoice_url"], style="success", icon_custom_emoji_id=ICON_IDS["cash"])],
        [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data=f"chk_inv_cb_{inv_id}", style="primary")]
    ])
    text = (
        f"📥 <b>Счёт CryptoBot создан</b>\n\n<blockquote>"
        f"Сумма: <b>{amount:.2f} USDT</b>\n"
        f"Тип: <b>{bonus_text}</b>\n"
        f"Бонус: <b>+{bonus_amount:.2f} $</b>\n"
        f"Отыгрыш: <b>{wager_required:.2f} $</b>\n"
        f"ID: <code>{inv_id}</code></blockquote>"
    )
    await safe_edit(call, text, kb)


@finance_router.callback_query(F.data.startswith("chk_inv_"))
async def check_invoice_status_callback(call: CallbackQuery):
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
        return await safe_edit(call, text, kb)
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


# ============================================================================
# CHECKS HANDLERS
# ============================================================================
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


# === ИСПРАВЛЕННАЯ ФУНКЦИЯ ОГРАНИЧЕНИЙ ЧЕКА ===
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

    # Кнопка привязки ТОЛЬКО для персонального чека
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


# === ИСПРАВЛЕНО: защита от привязки мультичека ===
@checks_router.callback_query(F.data.startswith("chk_set_user_"))
async def ask_check_target(call: CallbackQuery, state: FSMContext):
    code = call.data.replace("chk_set_user_", "")
    chk = await db_get_check(code)
    if not chk or chk["creator_id"] != call.from_user.id:
        return await call.answer("❌ Чек не найден.", show_alert=True)
    # ЗАЩИТА: мультичек нельзя привязать
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


# ============================================================================
# DICE GAME
# ============================================================================
DICE_BETS = [0.05, 0.1, 0.5, 1.0, 2.0, 5.0]


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


@dice_router.callback_query(F.data == "game_dice")
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


@dice_router.callback_query(F.data == "dice_change_bet")
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


@dice_router.callback_query(F.data.startswith("set_bet_"))
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


@dice_router.callback_query(F.data == "dice_m_exact")
async def choose_exact(call: CallbackQuery):
    kb = [
        [InlineKeyboardButton(text=f"🎲 {i}", callback_data=f"dice_exact_{i}", style="primary") for i in range(1, 4)],
        [InlineKeyboardButton(text=f"🎲 {i}", callback_data=f"dice_exact_{i}", style="primary") for i in range(4, 7)],
        [InlineKeyboardButton(text="Назад", callback_data="game_dice", style="danger", icon_custom_emoji_id=ICON_IDS["cross"])]
    ]
    await safe_edit(call, "🎯 <b>Выберите число (x6.0):</b>", InlineKeyboardMarkup(inline_keyboard=kb))


@dice_router.callback_query(F.data.startswith("dice_exact_"))
async def run_exact_action(call: CallbackQuery):
    target = int(call.data.split("_")[2])
    await run_dice_game(call, "Точное", 1,
                        lambda d: (d[0] == target, 6.0, f"Выпало {d[0]} (на {target})"))


@dice_router.callback_query(F.data == "dice_m_parity")
async def choose_parity(call: CallbackQuery):
    kb = [
        [
            InlineKeyboardButton(text="Чёт (x1.9)", callback_data="dice_par_even", style="primary"),
            InlineKeyboardButton(text="Нечет (x1.9)", callback_data="dice_par_odd", style="primary")
        ],
        [InlineKeyboardButton(text="Назад", callback_data="game_dice", style="danger", icon_custom_emoji_id=ICON_IDS["cross"])]
    ]
    await safe_edit(call, "⚖️ <b>Чёт или Нечет:</b>", InlineKeyboardMarkup(inline_keyboard=kb))


@dice_router.callback_query(F.data.startswith("dice_par_"))
async def run_parity_action(call: CallbackQuery):
    t = call.data.split("_")[2]
    await run_dice_game(call, "Чет/Нечет", 1,
                        lambda d: (((d[0] % 2 == 0) if t == "even" else (d[0] % 2 != 0)), 1.9, f"Выпало {d[0]}"))


@dice_router.callback_query(F.data == "dice_m_hl")
async def choose_hl(call: CallbackQuery):
    kb = [
        [
            InlineKeyboardButton(text="1-3 (x1.9)", callback_data="dice_hl_l", style="primary"),
            InlineKeyboardButton(text="4-6 (x1.9)", callback_data="dice_hl_h", style="primary")
        ],
        [InlineKeyboardButton(text="Назад", callback_data="game_dice", style="danger", icon_custom_emoji_id=ICON_IDS["cross"])]
    ]
    await safe_edit(call, "📊 <b>Больше/Меньше:</b>", InlineKeyboardMarkup(inline_keyboard=kb))


@dice_router.callback_query(F.data.startswith("dice_hl_"))
async def run_hl_action(call: CallbackQuery):
    t = call.data.split("_")[2]
    await run_dice_game(call, "Больше/Меньше", 1,
                        lambda d: (((d[0] <= 3) if t == "l" else (d[0] >= 4)), 1.9, f"Выпало {d[0]}"))


@dice_router.callback_query(F.data == "dice_m_seven")
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


@dice_router.callback_query(F.data.startswith("dice_sev_"))
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


@dice_router.callback_query(F.data == "dice_m_mult18")
async def choose_m18(call: CallbackQuery):
    kb = [
        [
            InlineKeyboardButton(text="18- (x1.2)", callback_data="dice_18_l", style="primary"),
            InlineKeyboardButton(text="18+ (x4.0)", callback_data="dice_18_h", style="danger", icon_custom_emoji_id=ICON_IDS["fire"])
        ],
        [InlineKeyboardButton(text="Назад", callback_data="game_dice", style="danger", icon_custom_emoji_id=ICON_IDS["cross"])]
    ]
    await safe_edit(call, f"{EMOJI['fire']} <b>Произведение кубиков:</b>", InlineKeyboardMarkup(inline_keyboard=kb))


@dice_router.callback_query(F.data.startswith("dice_18_"))
async def run_m18_action(call: CallbackQuery):
    t = call.data.split("_")[2]
    def eval_18(d):
        p = d[0] * d[1]
        desc = f"Выпало: {d[0]} * {d[1]} = {p}"
        if t == "l" and p < 18: return True, 1.2, desc
        if t == "h" and p >= 18: return True, 4.0, desc
        return False, 0.0, desc
    await run_dice_game(call, "18-умножение", 2, eval_18)


# ============================================================================
# MINES & TOWER
# ============================================================================
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


@games_router.message(Command("game_off"))
async def cmd_cancel_game(message: Message):
    uid = message.from_user.id
    async with get_lock(uid):
        deleted = await db_cancel_active_session(uid)
    if deleted:
        await message.reply(
            "🛑 <b>Игра отменена!</b>\n<blockquote>Сессия очищена.</blockquote>",
            parse_mode="HTML"
        )
    else:
        await message.reply("ℹ️ Нет активных игр.")


@games_router.callback_query(F.data == "game_provably_fair")
async def show_provably_fair_info(call: CallbackQuery):
    sess = await db_get_session(call.from_user.id)
    if not sess:
        return await call.answer("❌ Игра завершена.", show_alert=True)
    data = sess["data"]
    info_text = (
        f"🛡️ Provably Fair\n\nSHA-256 Hash:\n{data['hash']}\n\nСоль скрыта до конца игры."
    )
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


# ============================================================================
# SPORT HANDLERS
# ============================================================================
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
async def process_sport_bet_amount(message: Message, state: FSMContext):
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
    potential_win = round(amount * coef, 2)
    await message.reply(
        f"✅ <b>Ставка принята!</b>\n\n<blockquote>"
        f"Событие: <b>{team}</b>\n"
        f"Сумма: <b>{amount:.2f} $</b>\n"
        f"Коэф: <b>x{coef}</b>\n"
        f"Потенциальный выигрыш: <b>{potential_win:.2f} $</b>\n\n"
        f"ID ставки: <code>{bet_id}</code></blockquote>",
        parse_mode="HTML"
    )


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


# ============================================================================
# ADMIN SPORT
# ============================================================================
class AdminSportStates(StatesGroup):
    waiting_team1 = State()
    waiting_team2 = State()
    waiting_coef1 = State()
    waiting_coef2 = State()
    waiting_description = State()
    waiting_ai_prediction = State()
    waiting_lineups = State()


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
            text=f"❌ {ev['team1']} — {ev['team2']}",
            callback_data=f"adm_sport_del_{ev['id']}", style="danger"
        )])
    kb.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="adm_sport_menu", style="danger")])
    await safe_edit(call, "📋 <b>Активные события</b>\n<blockquote>Нажмите для деактивации:</blockquote>",
                    InlineKeyboardMarkup(inline_keyboard=kb))


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
    result = await db_resolve_sport_bet(bet_id, True)
    if result:
        try:
            await bot.send_message(
                result["user_id"],
                f"🎉 <b>Ставка на спорт выиграла!</b>\n\n<blockquote>"
                f"Сумма: <b>{result['amount']:.2f} $</b>\n"
                f"Коэф: <b>x{result['coef']}</b>\n"
                f"Выплата: <b>+{result['payout']:.2f} $</b></blockquote>",
                parse_mode="HTML"
            )
        except Exception:
            pass
        await call.answer(f"✅ Выигрыш! Начислено {result['payout']:.2f}$", show_alert=True)
    else:
        await call.answer("❌ Ошибка.", show_alert=True)
    await adm_sport_pending(call)


@admin_sport_router.callback_query(F.data.startswith("adm_sport_lost_"))
async def adm_sport_lost(call: CallbackQuery, bot: Bot):
    if not is_admin(call.from_user.id):
        return
    bet_id = int(call.data.replace("adm_sport_lost_", ""))
    result = await db_resolve_sport_bet(bet_id, False)
    if result:
        try:
            await bot.send_message(
                result["user_id"],
                f"😔 <b>Ставка проиграла.</b>\n\n<blockquote>Потеряно: <b>{result['amount']:.2f} $</b></blockquote>",
                parse_mode="HTML"
            )
        except Exception:
            pass
        await call.answer("Ставка рассчитана.", show_alert=True)
    else:
        await call.answer("❌ Ошибка.", show_alert=True)
    await adm_sport_pending(call)


# ============================================================================
# ADMIN PANEL
# ============================================================================
class AdminStates(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_promo_code = State()
    waiting_for_promo_reward = State()
    waiting_for_broadcast_text = State()


def admin_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👤 Управление игроком", callback_data="adm_find_user", style="primary"),
            InlineKeyboardButton(text="💳 Шлюзы", callback_data="adm_gateways_menu", style="primary")
        ],
        [
            InlineKeyboardButton(text="🎁 Создать промокод", callback_data="adm_create_promo", style="success", icon_custom_emoji_id=ICON_IDS["cash"]),
            InlineKeyboardButton(text="⚽ Спорт", callback_data="adm_sport_menu", style="primary", icon_custom_emoji_id=ICON_IDS["fire"])
        ],
        [
            InlineKeyboardButton(text="📢 Рассылка", callback_data="adm_broadcast_start", style="primary", icon_custom_emoji_id=ICON_IDS["fire"]),
            InlineKeyboardButton(text="📊 Статистика", callback_data="adm_stats", style="primary")
        ],
        [InlineKeyboardButton(text="♻️ Сбросить ТОП", callback_data="adm_reset_top", style="danger")]
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


@admin_router.callback_query(F.data == "adm_find_user")
async def ask_user_id(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.set_state(AdminStates.waiting_for_user_id)
    await safe_edit(call, "🔍 <b>Введите Telegram ID:</b>",
                    InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data="adm_main_menu", style="danger")]]))


@admin_router.message(AdminStates.waiting_for_user_id)
async def process_user_search(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        target_uid = int(message.text.strip())
    except ValueError:
        return await message.reply("❌ Числовой ID:")
    user = await get_user(target_uid)
    if not user:
        return await message.reply("❌ Не найден.")
    await state.clear()
    await message.reply(
        f"👤 ID: <code>{target_uid}</code>\nБаланс: <b>{user['balance']:.2f}$</b>",
        reply_markup=admin_main_kb(), parse_mode="HTML"
    )


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
    total = row[1] if row[1] else 0.0
    await safe_edit(call, f"📊 Юзеров: {row[0]} | Балансов: {total:.2f}$",
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
    for uid in uids:
        try:
            await message.bot.send_message(uid, message.text, parse_mode="HTML")
            await asyncio.sleep(0.04)
        except Exception:
            pass
    await state.clear()
    await message.reply("✅ Рассылка завершена!", reply_markup=admin_main_kb())


# ============================================================================
# QUICK COMMANDS
# ============================================================================
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
        f"{EMOJI['cash']} <b>Ставка обновлена!</b>\n\n"
        f"<blockquote>Новая ставка: <b>{new_bet:.2f} $</b></blockquote>",
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


# ============================================================================
# MAIN
# ============================================================================
logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s")


async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="🏠 Главное меню"),
        BotCommand(command="profile", description="👤 Профиль"),
        BotCommand(command="balance", description="💰 Баланс"),
        BotCommand(command="promo", description="🎁 Промокод"),
        BotCommand(command="game_off", description="🛑 Отменить игру"),
        BotCommand(command="admin", description="⚙️ Админ-панель"),
        BotCommand(command="send", description="💸 Перевод (в чате reply)"),
    ]
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())


async def main():
    await init_db()
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    dp.message.middleware(ThrottlingMiddleware())
    dp.callback_query.middleware(ThrottlingMiddleware())

    @dp.update.outer_middleware()
    async def debug_updates(handler, event: Update, data: dict):
        if event.message:
            logging.info(f"📥 @{event.message.from_user.username or event.message.from_user.id}: {event.message.text}")
        return await handler(event, data)

    dp.include_router(admin_router)
    dp.include_router(admin_sport_router)
    dp.include_router(finance_router)
    dp.include_router(checks_router)
    dp.include_router(games_router)
    dp.include_router(dice_router)
    dp.include_router(sport_router)
    dp.include_router(chat_router)
    dp.include_router(quick_router)
    dp.include_router(user_router)

    await bot.delete_webhook(drop_pending_updates=True)
    await set_bot_commands(bot)

    bot_info = await bot.get_me()
    logging.info(f"🤖 Бот запущен: @{bot_info.username} (ID: {bot_info.id})")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен.")
