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

# ====================== FALLBACK RESPONSES ======================
fallback_responses = [
    "💰 **Best Side Hustle 2026**: Affiliate Marketing with high-ticket products (software, courses, AI tools).",
    "🚀 **Fast Method**: Create and sell digital products like Notion templates, planners, or eBooks.",
    "📈 **Smart Strategy**: Build a Telegram channel and sell premium signals or exclusive content.",
    "🔥 **Quick Win**: Offer services on Fiverr like AI content, Telegram bots, or Canva designs.",
    "💡 **Key Rule**: Focus on solving expensive problems — people pay the most for money, health & time solutions.",
    "⚡ **Trend**: Telegram Mini Apps and paid communities are exploding right now."
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
    c.execute('''CREATE TABLE IF NOT EXISTS purchases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    product TEXT,
                    amount INTEGER,
                    date TEXT)''')
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

# ====================== AI RESPONSE ======================
def get_ai_response(prompt):
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
    return random.choice(fallback_responses) + "\n\n*💡 (Fallback Mode Active)*"

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
    bot.send_message(message.chat.id, "👋 Welcome to **MoneyMachine Bot** 🔥\n\nAlways ready to help!", reply_markup=main_menu())

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    bot.answer_callback_query(call.id)
    uid = call.from_user.id
    user = get_user(uid)

    if call.data == "ai":
        bot.send_message(call.message.chat.id, "🧠 Ask me anything about making money!")

    elif call.data == "btc":
        bot.send_message(call.message.chat.id, f"📈 **Bitcoin Price**: ${get_btc_price():,}")

    elif call.data == "premium":
        if user[2] == 1:
            bot.send_message(call.message.chat.id, "✅ You already have Premium!")
        else:
            send_invoice(call.message.chat.id, "Premium Monthly", "Unlimited AI + Daily Tips", 500, "premium_monthly")

    elif call.data == "refer":
        link = f"https://t.me/kkmachinebot?start=ref{uid}"
        bot.send_message(call.message.chat.id, f"🔗 Your Referral Link:\n`{link}`", parse_mode='Markdown')

    elif call.data == "shop":
        bot.send_message(call.message.chat.id, "🛒 Shop coming soon...")

# ====================== AI CHAT ======================
@bot.message_handler(func=lambda m: True)
def chat(message):
    user = get_user(message.from_user.id)
    if user[2] == 1 or user_free_queries[message.from_user.id] < 3:
        if not user[2]:
            user_free_queries[message.from_user.id] += 1
        response = get_ai_response(message.text)
        bot.reply_to(message, response)
    else:
        bot.reply_to(message, "💎 Free limit reached.\nUpgrade to Premium for unlimited access!")

def send_invoice(chat_id, title, desc, amount, payload):
    bot.send_invoice(chat_id, title, desc, payload, provider_token="", currency="XTR",
                     prices=[types.LabeledPrice(title, amount)])

@bot.pre_checkout_query_handler(func=lambda q: True)
def checkout(q):
    bot.answer_pre_checkout_query(q.id, ok=True)

def get_btc_price():
    try:
        r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd")
        return r.json()['bitcoin']['usd']
    except:
        return 0

print("🚀 MoneyMachine Bot v6.4 Running!")
bot.infinity_polling()
