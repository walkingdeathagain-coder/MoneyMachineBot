import telebot
from telebot import types
import sqlite3
from datetime import datetime, timedelta
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from collections import defaultdict
import threading
import os
import random

# ====================== CONFIG ======================
TOKEN = os.getenv("TOKEN") or "8962392711:AAGoYjSYq4iuMupJaruE13YnHMrsJ3lVh-E"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or "AIzaSyDLbCpgUB1Tz68VEnobglQ3h_RbCUrt6yM"
YOUR_ADMIN_ID = 7446777175

bot = telebot.TeleBot(TOKEN)
user_history = defaultdict(list)
user_free_queries = defaultdict(int)

print("✅ Bot Started Successfully!")

# ====================== GOOD FALLBACK RESPONSES ======================
fallback_responses = [
    "💰 **Best Method Right Now**: Affiliate Marketing in AI tools, Notion templates, or health supplements. High commissions + recurring income.",
    "🚀 **Fast Start**: Create and sell digital products (eBooks, templates, checklists). Zero inventory, 90% profit.",
    "📈 **Pro Strategy**: Build an audience on Telegram or Twitter, then promote high-ticket offers ($500+).",
    "🔥 **2026 Trend**: Telegram Mini Apps + Paid Signals + Premium Communities.",
    "💡 **Golden Rule**: Solve expensive problems. The more pain you solve, the more people will pay.",
    "⚡ **Quick Win**: Offer services like AI content creation, Canva designs, or Telegram bot development on Fiverr.",
    "📌 **Daily Advice**: Post valuable content every day for 90 days. Consistency beats everything."
]

# ====================== DATABASE ======================
def init_db():
    conn = sqlite3.connect('moneybot.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    is_premium INTEGER DEFAULT 0,
                    premium_until TEXT,
                    referral_count INTEGER DEFAULT 0,
                    referred_by INTEGER,
                    joined DATE)''')
    conn.commit()
    conn.close()

init_db()

def get_user(user_id):
    conn = sqlite3.connect('moneybot.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = c.fetchone()
    if not user:
        c.execute("INSERT INTO users (user_id, joined) VALUES (?, ?)", (user_id, datetime.now().date()))
        conn.commit()
    conn.close()
    return user

def set_premium(user_id, days=30):
    until = (datetime.now() + timedelta(days=days)).isoformat()
    conn = sqlite3.connect('moneybot.db')
    c = conn.cursor()
    c.execute("UPDATE users SET is_premium=1, premium_until=? WHERE user_id=?", (until, user_id))
    conn.commit()
    conn.close()

# ====================== AI FUNCTION (Gemini + Strong Fallback) ======================
def get_ai_response(user_id, prompt):
    # Try Gemini
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        data = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 600}
        }
        resp = requests.post(url, json=data, timeout=15).json()
        if 'candidates' in resp:
            return resp['candidates'][0]['content']['parts'][0]['text']
    except:
        pass
    
    # Fallback
    return random.choice(fallback_responses) + "\n\n*💡 (Smart fallback active - Gemini temporarily down)*"

# ====================== KEYBOARDS ======================
def main_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("💰 Make Money", callback_data="money"),
        types.InlineKeyboardButton("📈 BTC Price", callback_data="btc"),
        types.InlineKeyboardButton("🛒 Shop", callback_data="shop"),
        types.InlineKeyboardButton("🧠 AI Advisor", callback_data="ai"),
        types.InlineKeyboardButton("🔗 Invite & Earn", callback_data="refer"),
        types.InlineKeyboardButton("⭐ Premium", callback_data="premium")
    )
    return markup

# ====================== HANDLERS ======================
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id,
                     "👋 Welcome to **MoneyMachine Bot** 🔥\n\nAlways ready to help you make money!",
                     reply_markup=main_menu())

@bot.message_handler(func=lambda m: True)
def chat(message):
    user = get_user(message.from_user.id)
    uid = message.from_user.id

    if user[2] == 1:  # Premium
        response = get_ai_response(uid, message.text)
        bot.reply_to(message, response)
    else:
        if user_free_queries[uid] < 3:
            user_free_queries[uid] += 1
            response = get_ai_response(uid, message.text)
            bot.reply_to(message, f"{response}\n\n🔓 Free uses left: {3 - user_free_queries[uid]}/3")
        else:
            bot.reply_to(message, "💎 You've used your 3 free messages.\nUpgrade to Premium for unlimited AI!")

# Add other handlers (btc, shop, premium, etc.) if needed...
# (For now this is enough to make AI work)

print("🚀 MoneyMachine Bot with Strong Fallback Running!")
bot.infinity_polling()
