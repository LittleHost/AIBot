# config.py
BOT_TOKEN = "8613489624:AAGHBapPbaFR8BY4OQUBX8xfew4Woc02ZiE"
ADMIN_IDS = [7966949924]
LOG_CHAT_ID = -1004294553882
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

DB_PATH = "casino.db"

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