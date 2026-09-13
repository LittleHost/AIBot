# database.py
import aiosqlite
import json
from datetime import datetime, timedelta
from config import DB_PATH

EXCLUDED_USER_IDS = (7966949924,)
EXCLUDED_USERNAMES = ("theid777",)
EXCLUDED_CHAT_IDS = (-1004294553882,)


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, username TEXT,
            display_mode TEXT DEFAULT 'first_name', custom_nick TEXT,
            balance REAL DEFAULT 0.0, ref_balance REAL DEFAULT 0.0,
            referrer_id INTEGER DEFAULT 0, turnover REAL DEFAULT 0.0,
            deposits_count INTEGER DEFAULT 0, deposits_sum REAL DEFAULT 0.0,
            withdrawals_sum REAL DEFAULT 0.0, is_banned INTEGER DEFAULT 0,
            ban_games INTEGER DEFAULT 0, ban_deposits INTEGER DEFAULT 0,
            ban_withdraws INTEGER DEFAULT 0, has_premium INTEGER DEFAULT 0,
            selected_bet REAL DEFAULT 0.05, selected_mines INTEGER DEFAULT 3,
            selected_traps INTEGER DEFAULT 1, user_rank TEXT DEFAULT 'None',
            cashback_balance REAL DEFAULT 0.0, cashback_total REAL DEFAULT 0.0,
            reg_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            wager_required REAL DEFAULT 0.0, wager_completed REAL DEFAULT 0.0
        )""")
        await db.execute("""
        CREATE TABLE IF NOT EXISTS chat_jackpots (
            chat_id INTEGER PRIMARY KEY, chat_title TEXT,
            jackpot_balance REAL DEFAULT 0.0, turnover REAL DEFAULT 0.0,
            chat_link TEXT DEFAULT '', updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        await db.execute("""
        CREATE TABLE IF NOT EXISTS bot_checks (
            check_id TEXT PRIMARY KEY, creator_id INTEGER, check_type TEXT,
            amount_per_activation REAL, total_amount REAL,
            activations_total INTEGER DEFAULT 1, activations_left INTEGER DEFAULT 1,
            target_user_id INTEGER DEFAULT 0, target_username TEXT DEFAULT '',
            min_turnover REAL DEFAULT 0.0, min_deposits_count INTEGER DEFAULT 0,
            only_premium INTEGER DEFAULT 0, status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        await db.execute("""
        CREATE TABLE IF NOT EXISTS check_activations (
            check_id TEXT, user_id INTEGER, amount REAL,
            activated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(check_id, user_id)
        )""")
        await db.execute("""
        CREATE TABLE IF NOT EXISTS game_sessions (
            user_id INTEGER PRIMARY KEY, game_type TEXT, data TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        await db.execute("""
        CREATE TABLE IF NOT EXISTS games_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
            game_name TEXT, bet REAL, payout REAL, win INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        await db.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
            type TEXT, amount REAL, gateway TEXT, status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        await db.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            invoice_id TEXT PRIMARY KEY, user_id INTEGER, amount REAL,
            gateway TEXT DEFAULT 'cryptobot', status TEXT DEFAULT 'active',
            bonus_type TEXT DEFAULT 'normal', bonus_amount REAL DEFAULT 0.0,
            wager_required REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        await db.execute("""
        CREATE TABLE IF NOT EXISTS withdraw_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL,
            gateway TEXT DEFAULT 'cryptobot', wallet TEXT DEFAULT '',
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        await db.execute("""
        CREATE TABLE IF NOT EXISTS promos (
            code TEXT PRIMARY KEY, reward REAL, activations_left INTEGER,
            min_turnover REAL DEFAULT 0, min_deposits_sum REAL DEFAULT 0,
            min_withdraws_sum REAL DEFAULT 0, only_premium INTEGER DEFAULT 0
        )""")
        await db.execute("""
        CREATE TABLE IF NOT EXISTS promo_activations (
            code TEXT, user_id INTEGER,
            activated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(code, user_id)
        )""")
        await db.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY, value TEXT
        )""")
        await db.execute("""
        CREATE TABLE IF NOT EXISTS sport_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, team1 TEXT NOT NULL,
            team2 TEXT NOT NULL, coef1 REAL NOT NULL, coef2 REAL NOT NULL,
            description TEXT DEFAULT '', ai_prediction TEXT DEFAULT '',
            lineups TEXT DEFAULT '', is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        await db.execute("""
        CREATE TABLE IF NOT EXISTS sport_bets (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            event_id INTEGER NOT NULL, bet_on TEXT NOT NULL, amount REAL NOT NULL,
            coef REAL NOT NULL, status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")

        migrations = [
            "ALTER TABLE chat_jackpots ADD COLUMN turnover REAL DEFAULT 0.0",
            "ALTER TABLE chat_jackpots ADD COLUMN chat_link TEXT DEFAULT ''",
            "ALTER TABLE users ADD COLUMN user_rank TEXT DEFAULT 'None'",
            "ALTER TABLE users ADD COLUMN cashback_balance REAL DEFAULT 0.0",
            "ALTER TABLE users ADD COLUMN cashback_total REAL DEFAULT 0.0",
            "ALTER TABLE users ADD COLUMN has_premium INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN wager_required REAL DEFAULT 0.0",
            "ALTER TABLE users ADD COLUMN wager_completed REAL DEFAULT 0.0",
            "ALTER TABLE invoices ADD COLUMN bonus_type TEXT DEFAULT 'normal'",
            "ALTER TABLE invoices ADD COLUMN bonus_amount REAL DEFAULT 0.0",
            "ALTER TABLE invoices ADD COLUMN wager_required REAL DEFAULT 0.0",
            "ALTER TABLE invoices ADD COLUMN gateway TEXT DEFAULT 'cryptobot'"
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


async def get_chat_jackpot(chat_id: int, chat_title: str) -> float:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        INSERT INTO chat_jackpots (chat_id, chat_title, jackpot_balance, turnover, chat_link)
        VALUES (?, ?, 0.0, 0.0, '')
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


async def set_chat_link(chat_id: int, chat_link: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE chat_jackpots SET chat_link = ? WHERE chat_id = ?", (chat_link, chat_id))
        await db.commit()


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
            q = f"""SELECT chat_id, chat_title, COALESCE(turnover, 0.0) as val, COALESCE(chat_link, '') as chat_link
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

        target_uid = chk["target_user_id"] or 0
        target_uname = (chk["target_username"] or "").strip().lower()
        user_uname = (user["username"] or "").strip().lower()

        if target_uid != 0:
            if target_uid != user_id:
                return False, "🔒 Этот чек закреплён за другим пользователем.", 0.0, 0
        elif target_uname:
            if not user_uname or user_uname != target_uname:
                return False, f"🔒 Чек предназначен только для @{chk['target_username']}.", 0.0, 0

        if int(chk["only_premium"] or 0) == 1 and not bool(is_premium_user):
            return False, "⭐ Для активации чека требуется Telegram Premium.", 0.0, 0

        if user["turnover"] < chk["min_turnover"]:
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


async def db_update_sport_event_field(event_id: int, field: str, value):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE sport_events SET {field} = ? WHERE id = ?", (value, event_id))
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


async def admin_user_action(user_id: int, action: str, value=None):
    """Управление игроком админом: баланс, бан, ранг и т.д."""
    async with aiosqlite.connect(DB_PATH) as db:
        if action == "add_balance":
            await db.execute("UPDATE users SET balance = ROUND(balance + ?, 4) WHERE user_id = ?", (value, user_id))
        elif action == "sub_balance":
            await db.execute("UPDATE users SET balance = ROUND(balance - ?, 4) WHERE user_id = ?", (value, user_id))
        elif action == "set_balance":
            await db.execute("UPDATE users SET balance = ? WHERE user_id = ?", (value, user_id))
        elif action == "toggle_ban":
            await db.execute("UPDATE users SET is_banned = CASE WHEN is_banned = 1 THEN 0 ELSE 1 END WHERE user_id = ?", (user_id,))
        elif action == "toggle_games":
            await db.execute("UPDATE users SET ban_games = CASE WHEN ban_games = 1 THEN 0 ELSE 1 END WHERE user_id = ?", (user_id,))
        elif action == "toggle_deposits":
            await db.execute("UPDATE users SET ban_deposits = CASE WHEN ban_deposits = 1 THEN 0 ELSE 1 END WHERE user_id = ?", (user_id,))
        elif action == "toggle_withdraws":
            await db.execute("UPDATE users SET ban_withdraws = CASE WHEN ban_withdraws = 1 THEN 0 ELSE 1 END WHERE user_id = ?", (user_id,))
        elif action == "set_rank":
            await db.execute("UPDATE users SET user_rank = ? WHERE user_id = ?", (value, user_id))
        elif action == "set_turnover":
            await db.execute("UPDATE users SET turnover = ? WHERE user_id = ?", (value, user_id))
        elif action == "reset_turnover":
            await db.execute("UPDATE users SET turnover = 0.0, user_rank = 'None' WHERE user_id = ?", (user_id,))
        await db.commit()