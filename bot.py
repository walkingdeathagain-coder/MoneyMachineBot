import telebot
from telebot import types
import sqlite3
from datetime import datetime, timedelta
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from collections import defaultdict
import threading
import os

# ====================== CONFIG ======================
TOKEN = os.getenv("TOKEN") or "8962392711:AAGoYjSYq4iuMupJaruE13YnHMrsJ3lVh-E"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or "AIzaSyDLbCpgUB1Tz68VEnobglQ3h_RbCUrt6yM"
YOUR_ADMIN_ID = 7446777175

bot = telebot.TeleBot(TOKEN)
user_history = defaultdict(list)
user_free_queries = defaultdict(int)

print("✅ Bot Started Successfully!")

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
        user = (user_id, None, 0, None, 0, None, datetime.now().date())
    conn.close()
    return user

def set_premium(user_id, days=30):
    until = (datetime.now() + timedelta(days=days)).isoformat()
    conn = sqlite3.connect('moneybot.db')
    c = conn.cursor()
    c.execute("UPDATE users SET is_premium=1, premium_until=? WHERE user_id=?", (until, user_id))
    conn.commit()
    conn.close()

def add_referral(referred_id, referrer_id):
    conn = sqlite3.connect('moneybot.db')
    c = conn.cursor()
    c.execute("UPDATE users SET referred_by=? WHERE user_id=?", (referrer_id, referred_id))
    c.execute("UPDATE users SET referral_count = referral_count + 1 WHERE user_id=?", (referrer_id,))
    conn.commit()
    
    c.execute("SELECT referral_count FROM users WHERE user_id=?", (referrer_id,))
    count = c.fetchone()[0]
    if count % 3 == 0 and count > 0:
        set_premium(referrer_id, 30)
        try:
            bot.send_message(referrer_id, "🎁 **Referral Reward!** You earned 1 Free Premium Month!")
        except:
            pass

# ====================== IMPROVED Gemini AI ======================
def ask_gemini(user_id, prompt):
    if len(user_history[user_id]) > 10:
        user_history[user_id] = user_history[user_id][-8:]
    
    history = user_history[user_id][-8:]
    full_prompt = "\n".join(history) + f"\nUser: {prompt}\nYou are a world-class money making expert. Give practical, short and actionable advice."

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        data = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 700
            }
        }
        resp = requests.post(url, json=data, timeout=25).json()
        
        if 'candidates' in resp and len(resp['candidates']) > 0:
            answer = resp['candidates'][0]['content']['parts'][0]['text']
            user_history[user_id].append(f"User: {prompt}")
            user_history[user_id].append(f"AI: {answer[:400]}...")
            return answer
        else:
            return "❌ AI service is busy. Please try again in 10 seconds."
            
    except Exception as e:
        print("AI Error:", e)
        return "❌ AI is temporarily unavailable.\nPlease try again or upgrade to Premium."

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

# ====================== COMMANDS ======================
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    args = message.text.split()
    
    if len(args) > 1 and args[1].startswith("ref"):
        try:
            referrer = int(args[1][3:])
            if referrer != user_id:
                add_referral(user_id, referrer)
        except:
            pass

    bot.send_message(message.chat.id,
                     "👋 Welcome to **MoneyMachine Bot** 🔥\n\n"
                     "Real AI • Daily Tips • Shop • Refer & Earn",
                     reply_markup=main_menu())

@bot.message_handler(commands=['myplan'])
def myplan(message):
    user = get_user(message.from_user.id)
    if user[2] == 1:
        bot.send_message(message.chat.id, "✅ **Premium Active**")
    else:
        bot.send_message(message.chat.id, "🆓 You are on Free Plan.\nUpgrade for unlimited AI!")

# ====================== CALLBACKS ======================
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    bot.answer_callback_query(call.id)
    uid = call.from_user.id
    user = get_user(uid)

    if call.data == "btc":
        price = get_btc_price()
        bot.send_message(call.message.chat.id, f"📈 **Bitcoin Price**: ${price:,} USD")

    elif call.data == "money":
        bot.send_message(call.message.chat.id, "💰 Choose a method:", reply_markup=get_money_menu())

    elif call.data == "shop":
        bot.send_message(call.message.chat.id, "🛒 **Digital Store**", reply_markup=get_shop_menu())

    elif call.data == "premium":
        if user[2] == 1:
            bot.send_message(call.message.chat.id, "✅ You already have Premium!")
        else:
            send_invoice(call.message.chat.id, "Premium Monthly", "Unlimited AI + Daily Tips", 500, "premium_monthly")

    elif call.data == "ai":
        bot.send_message(call.message.chat.id, "🧠 Ask me anything about making money!")

    elif call.data == "refer":
        link = f"https://t.me/kkmachinebot?start=ref{uid}"
        bot.send_message(call.message.chat.id, f"🔗 **Your Referral Link**\n`{link}`\n\nEvery 3 referrals = 1 Free Month!", parse_mode='Markdown')

    elif call.data.startswith("buy_"):
        product = call.data.replace("buy_", "")
        prices = {"affiliate":(150,"Affiliate Mastery"), "signals":(300,"Crypto Signals"), 
                  "dropship":(250,"Dropshipping Kit"), "notion":(200,"Notion System"), 
                  "ecom":(350,"E-commerce Mastery")}
        amount, title = prices.get(product, (150, "Digital Product"))
        send_invoice(call.message.chat.id, title, "Instant delivery", amount, f"buy_{product}")

def get_shop_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📘 Affiliate - 150 Stars", callback_data="buy_affiliate"),
        types.InlineKeyboardButton("📊 Signals - 300 Stars", callback_data="buy_signals"),
        types.InlineKeyboardButton("🚀 Dropshipping - 250 Stars", callback_data="buy_dropship"),
        types.InlineKeyboardButton("📋 Notion - 200 Stars", callback_data="buy_notion"),
        types.InlineKeyboardButton("🛍️ E-commerce - 350 Stars", callback_data="buy_ecom")
    )
    return markup

def get_money_menu():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Free Tips", callback_data="free_tips"))
    return markup

# ====================== PAYMENTS ======================
def send_invoice(chat_id, title, desc, amount, payload):
    bot.send_invoice(chat_id, title, desc, payload, provider_token="", currency="XTR",
                     prices=[types.LabeledPrice(title, amount)])

@bot.pre_checkout_query_handler(func=lambda q: True)
def checkout(q):
    bot.answer_pre_checkout_query(q.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def successful_payment(message):
    payload = message.successful_payment.invoice_payload
    uid = message.from_user.id
    if "premium" in payload:
        set_premium(uid, 30)
        bot.send_message(uid, "🎉 **Premium Activated!** Unlimited AI unlocked!")
    else:
        product = payload.replace("buy_", "")
        bot.send_message(uid, f"✅ Payment Successful!")
        deliver_product(uid, product)

def deliver_product(chat_id, product):
    bot.send_message(chat_id, "📥 **Your Product is Ready**\n\nhttps://t.me/kkmachinebot\n(Change this link later)")

# ====================== AI CHAT ======================
@bot.message_handler(func=lambda m: True)
def chat(message):
    user = get_user(message.from_user.id)
    uid = message.from_user.id
    if user[2] == 1:
        response = ask_gemini(uid, message.text)
        bot.reply_to(message, response)
    else:
        if user_free_queries[uid] < 3:
            user_free_queries[uid] += 1
            response = ask_gemini(uid, message.text)
            bot.reply_to(message, f"{response}\n\n🔓 Free uses left: {3 - user_free_queries[uid]}/3")
        else:
            bot.reply_to(message, "💎 Free limit reached.\nUpgrade to Premium for unlimited AI!")

# ====================== DAILY TIPS ======================
def send_daily_tips():
    try:
        conn = sqlite3.connect('moneybot.db')
        c = conn.cursor()
        c.execute("SELECT user_id FROM users WHERE is_premium=1")
        users = [row[0] for row in c.fetchall()]
        conn.close()

        tip = ask_gemini(0, "Give one powerful short money-making tip today")
        for uid in users:
            try:
                bot.send_message(uid, f"📅 **Daily Money Tip**\n\n{tip}")
            except:
                pass
    except:
        pass

# ====================== SCHEDULER ======================
scheduler = BackgroundScheduler()

def start_scheduler():
    scheduler.add_job(send_daily_tips, 'cron', hour=9, minute=0)
    scheduler.start()

threading.Thread(target=start_scheduler, daemon=True).start()

def get_btc_price():
    try:
        r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd", timeout=10)
        return r.json()['bitcoin']['usd']
    except:
        return 0

# ====================== ADMIN ======================
@bot.message_handler(commands=['admin'])
def admin(message):
    if message.from_user.id != YOUR_ADMIN_ID: return
    bot.send_message(message.chat.id, "🛠️ Admin Panel\n/stats\n/broadcast <text>")

@bot.message_handler(commands=['stats'])
def stats(message):
    if message.from_user.id != YOUR_ADMIN_ID: return
    conn = sqlite3.connect('moneybot.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE is_premium=1")
    premium = c.fetchone()[0]
    bot.send_message(message.chat.id, f"📊 Total Users: {total}\nPremium: {premium}")

print("🚀 MoneyMachine Bot v6.3 Running!")
bot.infinity_polling()
