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
    "💡 **Top Side Hustle Right Now**: Start Affiliate Marketing in high-ticket niches like software, coaching, or health supplements. Many are earning $3k–$10k/month.",
    "🚀 **Best Beginner Method**: Create digital products (Notion templates, eBooks, checklists) and sell them on Gumroad or Telegram.",
    "📈 **Pro Tip**: Focus on solving painful problems. People pay the most for solutions to money, health, and relationships.",
    "🔥 **Fast Money Idea**: Offer services on Fiverr/Upwork like Telegram bot development, Canva designs, or AI prompt engineering.",
    "💰 **2026 Trend**: Build Telegram Mini Apps and monetize with ads + premium features.",
    "📌 **Golden Rule**: Consistency beats talent. Post daily content in your niche for 90 days."
]

# ====================== DATABASE ======================
def init_db():
    conn = sqlite3.connect('moneybot.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (...)''')  # shortened for space
    # (keeping same as before)
    conn.commit()
    conn.close()

init_db()

# ... (I'll keep other functions short for now)

def get_user(user_id):
    # same as previous versions
    conn = sqlite3.connect('moneybot.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = c.fetchone()
    if not user:
        c.execute("INSERT INTO users (user_id, joined) VALUES (?, ?)", (user_id, datetime.now().date()))
        conn.commit()
    conn.close()
    return user

# ====================== SMART AI FUNCTION ======================
def ask_gemini_or_fallback(user_id, prompt):
    # Try Gemini first
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        data = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 600}
        }
        resp = requests.post(url, json=data, timeout=20).json()
        
        if 'candidates' in resp:
            answer = resp['candidates'][0]['content']['parts'][0]['text']
            return answer
    except:
        pass
    
    # Fallback if Gemini fails
    return random.choice(fallback_responses) + "\n\n💡 *Powered by built-in knowledge (Gemini temporarily unavailable)*"

# ====================== MAIN MENU & COMMANDS ======================
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

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "👋 Welcome to **MoneyMachine Bot** 🔥\n\nReal value delivered even if AI is busy!", reply_markup=main_menu())

@bot.message_handler(func=lambda m: True)
def chat(message):
    user = get_user(message.from_user.id)
    uid = message.from_user.id
    
    if user[2] == 1:   # Premium
        response = ask_gemini_or_fallback(uid, message.text)
        bot.reply_to(message, response)
    else:
        if user_free_queries[uid] < 3:
            user_free_queries[uid] += 1
            response = ask_gemini_or_fallback(uid, message.text)
            bot.reply_to(message, f"{response}\n\n🔓 Free uses left: {3 - user_free_queries[uid]}/3")
        else:
            bot.reply_to(message, "💎 Free limit reached.\nUpgrade to Premium for unlimited AI + priority access!")

print("🚀 MoneyMachine Bot with Smart Fallback Running!")
bot.infinity_polling()
