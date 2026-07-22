import logging
import aiohttp
import json
import random
import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = '8826554842:AAE-mXvzJZWHZcVHIYrJh6umhrNVWRRam4E'
GITHUB_TOKEN = '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'
ADMIN_ID = 7966949924

# ============= БАЗА ДАННЫХ =============
def init_db():
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, banned INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

def is_banned(user_id):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute("SELECT banned FROM users WHERE user_id=?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result and result[0] == 1

def ban_user(user_id):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO users (user_id, banned) VALUES (?, 1)", (user_id,))
    conn.commit()
    conn.close()

def unban_user(user_id):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    users = [row[0] for row in c.fetchall()]
    conn.close()
    return users

# ============= ФИЛЬТРЫ =============
BAD_WORDS = [
    'хуй', 'пизда', 'бля', 'сука', 'нахуй', 'ебать', 'ебал', 'ебаный', 'ебанутый',
    'хуесос', 'пиздец', 'залупа', 'мудак', 'говно', 'гандон', 'шлюха', 'курва',
    'nigger', 'nigga', 'faggot', 'retard', 'chink', 'kike', 'spic',
    'негр', 'жид', 'хохол', 'чурка', 'хач', 'пидор',
    'секс', 'трах', 'порно', 'голая', 'голый', 'сиськи', 'писька',
    'минет', 'орал', 'анал', 'ролевая', 'ролевую', 'днд',
    'играть', 'поиграем', 'игры', 'геймплей', 'игровой', 'поиграть', 'сыграем'
]

RACIST_WORDS = ['негр', 'жид', 'хохол', 'чурка', 'хач', 'nigger', 'nigga', 'chink', 'kike', 'spic']

def contains_bad_words(text: str) -> bool:
    text_lower = text.lower()
    for word in BAD_WORDS:
        if word in text_lower:
            return True
    return False

def contains_racism(text: str) -> bool:
    text_lower = text.lower()
    for word in RACIST_WORDS:
        if word in text_lower:
            return True
    return False

# ============= GITHUB AI =============
API_URL = "https://models.inference.ai.azure.com/chat/completions"
MODELS = [
    "gpt-4o-mini",
    "meta-llama-3.1-8b-instruct",
    "cohere-command-r-plus",
    "mistral-large-2407",
    "phi-3-medium-128k-instruct",
    "gemma-2-27b-it"
]
model_stats = {model: {"requests": 0} for model in MODELS}

def get_next_model():
    min_requests = min(model_stats[model]["requests"] for model in MODELS)
    available = [m for m in MODELS if model_stats[m]["requests"] == min_requests]
    chosen = random.choice(available)
    model_stats[chosen]["requests"] += 1
    return chosen

async def get_ai_response(text: str, username: str = None) -> str:
    # Сначала проверяем на запрещенный контент
    if contains_bad_words(text):
        return "⚠️ Ваше сообщение содержит запрещенные слова (мат, 18+, игры, ролевые игры). Пожалуйста, соблюдайте правила."
    
    if contains_racism(text):
        return "🚫 Расизм и оскорбления по национальному признаку строго запрещены!"

    for _ in range(len(MODELS)):
        model = get_next_model()
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": f"""Ты - нейросеть Пипися АИ. Владелец: @theid777.
Ты работаешь только в чатах и отвечаешь на вопросы пользователей.
Твои строгие правила:
1. НИКОГДА не участвуй в ролевых играх
2. НИКОГДА не обсуждай игры и игровой процесс
3. НИКОГДА не отвечай на 18+ темы
4. НИКОГДА не используй мат и оскорбления
5. Отвечай кратко, по делу, дружелюбно
6. Если тебя спрашивают "кто ты" - отвечай: "Я нейросеть Пипися АИ - владелец: @theid777"
7. Если просят поиграть - вежливо откажись
8. Отвечай на русском языке

Ты - полезный помощник, который отвечает на вопросы, но с четкими ограничениями."""},
                {"role": "user", "content": text}
            ],
            "temperature": 0.7,
            "max_tokens": 500,
            "top_p": 0.95
        }
        headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Content-Type": "application/json"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(API_URL, json=payload, headers=headers, timeout=60) as response:
                    if response.status == 200:
                        data = await response.json()
                        model_stats[model]["requests"] = 0
                        return data["choices"][0]["message"]["content"]
                    elif response.status == 429:
                        model_stats[model]["requests"] = 9999
                        continue
        except Exception as e:
            logger.warning(f"Модель {model} ошибка: {e}")
            continue
    
    return "⚠️ Извините, я временно не могу ответить. Попробуйте позже."

# ============= КОМАНДЫ =============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type
    chat_title = update.effective_chat.title or "без названия"
    
    if is_banned(user_id):
        await update.message.reply_text("❌ Вы заблокированы!")
        return
    
    # ЛИЧНЫЕ СООБЩЕНИЯ
    if chat_type == "private":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💭 Добавить в чат", url="https://t.me/PipisyaAI_bot?startgroup=true")]
        ])
        await update.message.reply_text(
            text="⚙️ | Привет я @PipisyaAI_bot - нейросеть которая работает только в чатах.",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        return
    
    # ЧАТЫ
    if chat_type in ["group", "supergroup"]:
        # Проверяем, не админ ли это (для настройки)
        await update.message.reply_text(
            text=f"💭 | Привет чат | {chat_title}\n⚙️ | Я нейросеть Пипися АИ\nНапиши пипися вопрос - дабы я ответил на твой вопрос, удачи!",
            parse_mode=ParseMode.HTML
        )

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ У вас нет доступа!")
        return
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Рассылка", callback_data="broadcast")],
        [InlineKeyboardButton("🔒 Заблокировать", callback_data="ban")],
        [InlineKeyboardButton("🔓 Разблокировать", callback_data="unban")]
    ])
    
    await update.message.reply_text(
        text="👑 <b>Админ-панель</b>\n\nВыберите действие:",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if user_id != ADMIN_ID:
        await query.message.reply_text("❌ У вас нет доступа!")
        return
    
    data = query.data
    
    if data == "broadcast":
        await query.message.reply_text("📢 Введите текст для рассылки:")
        context.user_data['admin_action'] = 'broadcast'
    
    elif data == "ban":
        await query.message.reply_text("🔒 Введите ID пользователя для блокировки:")
        context.user_data['admin_action'] = 'ban'
    
    elif data == "unban":
        await query.message.reply_text("🔓 Введите ID пользователя для разблокировки:")
        context.user_data['admin_action'] = 'unban'

async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    action = context.user_data.get('admin_action')
    text = update.message.text
    
    if user_id != ADMIN_ID:
        return
    
    if action == 'broadcast':
        users = get_all_users()
        sent = 0
        for uid in users:
            try:
                await context.bot.send_message(
                    chat_id=uid,
                    text=f"📢 <b>Объявление</b>\n\n{text}",
                    parse_mode=ParseMode.HTML
                )
                sent += 1
            except:
                pass
        await update.message.reply_text(f"✅ Рассылка отправлена {sent} пользователям!")
        context.user_data['admin_action'] = None
    
    elif action == 'ban':
        try:
            target_id = int(text.strip())
            ban_user(target_id)
            await update.message.reply_text(f"✅ Пользователь {target_id} заблокирован!")
        except:
            await update.message.reply_text("❌ Введите корректный ID")
        context.user_data['admin_action'] = None
    
    elif action == 'unban':
        try:
            target_id = int(text.strip())
            unban_user(target_id)
            await update.message.reply_text(f"✅ Пользователь {target_id} разблокирован!")
        except:
            await update.message.reply_text("❌ Введите корректный ID")
        context.user_data['admin_action'] = None

# ============= ОТВЕТ НА СООБЩЕНИЯ =============
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_type = update.effective_chat.type
    message_text = update.message.text
    
    if not message_text:
        return
    
    # Проверка бана
    if is_banned(user_id):
        await update.message.reply_text("❌ Вы заблокированы!")
        return
    
    # Админ-действия
    if user_id == ADMIN_ID and context.user_data.get('admin_action'):
        await handle_admin_message(update, context)
        return
    
    # ОТВЕЧАЕМ ТОЛЬКО В ЧАТАХ (не в личке)
    if chat_type in ["group", "supergroup"]:
        # Проверяем, что обращаются к боту
        bot_username = (await context.bot.get_me()).username
        if f"@{bot_username}" in message_text or "пипися" in message_text.lower() or "pipisya" in message_text.lower():
            # Убираем упоминание из текста
            clean_text = message_text.replace(f"@{bot_username}", "").strip()
            if not clean_text:
                clean_text = "привет"
            
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
            
            username = update.effective_user.username or "User"
            reply = await get_ai_response(clean_text, username)
            
            # Форматируем ответ с именем пользователя
            final_reply = f"[{username}], {reply}"
            
            await update.message.reply_text(
                text=final_reply,
                parse_mode=ParseMode.HTML
            )
            return
    
    # В личке просто напоминаем
    if chat_type == "private" and not update.message.text.startswith('/'):
        await update.message.reply_text(
            text="⚙️ | Я нейросеть Пипися АИ, я работаю только в чатах!\nДобавь меня в группу: @PipisyaAI_bot",
            parse_mode=ParseMode.HTML
        )

# ============= ЗАПУСК =============
def main():
    init_db()
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("🚀 Бот Пипися AI запущен!")
    application.run_polling()

if __name__ == '__main__':
    main()
