import os
import sqlite3
import logging
from datetime import datetime, timedelta

import requests

from telegram import (
    Update,
    ReplyKeyboardMarkup,
)

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# =========================================
# CONFIG
# =========================================

TOKEN = "8787667902:AAGmQKmePgm2-pUD25oOwSuGn5mSN9elL0w"

ADMIN_ID = 7355302122

GROUP_ID = -1003944904264

VIP_LINK = "https://t.me/+z0zKkLWDdps4OGQ0"

# =========================================
# PAYHERO API
# =========================================

PAYHERO_USERNAME = "cT1F4Py83BsCQVx5H0Fs"

PAYHERO_PASSWORD = "bWVYoV5SbWts5kwLr5Y40TewMqYRpWnDpvGTZEPX"

CHANNEL_ID = 8506

PAYHERO_URL = "https://backend.payhero.co.ke/api/v2/payments"

# =========================================
# LOGGING
# =========================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)

# =========================================
# DATABASE
# =========================================

conn = sqlite3.connect("vip_users.db", check_same_thread=False)

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    full_name TEXT,
    plan TEXT,
    expiry TEXT
)
""")

conn.commit()

# =========================================
# PLANS
# =========================================

PLANS = {
    "📅 Daily": {
        "price": 50,
        "days": 1,
    },

    "⭐ Basic": {
        "price": 200,
        "days": 7,
    },

    "🔥 Standard": {
        "price": 500,
        "days": 30,
    },

    "👑 Premium": {
        "price": 1200,
        "days": 90,
    },
}

# =========================================
# KEYBOARD
# =========================================

keyboard = ReplyKeyboardMarkup(
    [
        ["📅 Daily", "⭐ Basic"],
        ["🔥 Standard", "👑 Premium"],
        ["⏳ My Subscription", "📞 Support"]
    ],
    resize_keyboard=True
)

# =========================================
# START
# =========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = """
🔥 WELCOME TO SIXTWO VIP BOT 🔥

Choose a package below 👇
"""

    await update.message.reply_text(
        text,
        reply_markup=keyboard
    )

# =========================================
# SEND STK PUSH
# =========================================

def send_stk(phone, amount):

    payload = {
        "phone_number": phone,
        "amount": amount,
        "channel_id": CHANNEL_ID,
        "provider": "m-pesa"
    }

    headers = {
        "Content-Type": "application/json"
    }

    try:

        response = requests.post(
            PAYHERO_URL,
            json=payload,
            headers=headers,
            auth=(PAYHERO_USERNAME, PAYHERO_PASSWORD),
            timeout=30
        )

        logger.info(response.text)

        if response.status_code in [200, 201, 202]:
            return True

        return False

    except Exception as e:
        logger.error(e)
        return False

# =========================================
# SAVE USER
# =========================================

def save_user(user, plan_name):

    days = PLANS[plan_name]["days"]

    expiry = datetime.now() + timedelta(days=days)

    cursor.execute("""
    INSERT OR REPLACE INTO users
    (user_id, username, full_name, plan, expiry)
    VALUES (?, ?, ?, ?, ?)
    """, (
        user.id,
        user.username,
        user.full_name,
        plan_name,
        expiry.isoformat()
    ))

    conn.commit()

    return expiry

# =========================================
# CHECK SUBSCRIPTION
# =========================================

async def check_subscription(update: Update):

    user_id = update.message.from_user.id

    cursor.execute(
        "SELECT plan, expiry FROM users WHERE user_id=?",
        (user_id,)
    )

    result = cursor.fetchone()

    if not result:

        await update.message.reply_text(
            "❌ No active subscription found."
        )

        return

    plan, expiry = result

    expiry_date = datetime.fromisoformat(expiry)

    remaining = expiry_date - datetime.now()

    if remaining.total_seconds() <= 0:

        await update.message.reply_text(
            "❌ Your subscription expired."
        )

        return

    await update.message.reply_text(
        f"""
✅ ACTIVE SUBSCRIPTION

📦 Plan: {plan}

⏳ Remaining Days: {remaining.days}

📅 Expiry:
{expiry_date.strftime('%d %b %Y')}
"""
    )

# =========================================
# HANDLE MESSAGES
# =========================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text

    # =========================
    # PLAN SELECTED
    # =========================

    if text in PLANS:

        context.user_data["selected_plan"] = text

        plan = PLANS[text]

        await update.message.reply_text(
            f"""
{text}

💰 Price: KES {plan['price']}

📲 Send your M-PESA number.

Example:
0712345678
"""
        )

        return

    # =========================
    # CHECK SUBSCRIPTION
    # =========================

    if text == "⏳ My Subscription":

        await check_subscription(update)

        return

    # =========================
    # SUPPORT
    # =========================

    if text == "📞 Support":

        await update.message.reply_text(
            "📞 Contact admin for support."
        )

        return

    # =========================
    # PHONE NUMBER
    # =========================

    if "selected_plan" not in context.user_data:
        return

    phone = text.strip()

    if not phone.startswith("07") or len(phone) != 10:

        await update.message.reply_text(
            "❌ Invalid phone number.\nUse 0712345678"
        )

        return

    plan_name = context.user_data["selected_plan"]

    amount = PLANS[plan_name]["price"]

    await update.message.reply_text(
        "⏳ Sending STK Push..."
    )

    success = send_stk(phone, amount)

    if not success:

        await update.message.reply_text(
            "❌ Failed to send STK Push."
        )

        return

    expiry = save_user(
        update.message.from_user,
        plan_name
    )

    await update.message.reply_text(
        f"""
✅ PAYMENT RECEIVED

🎉 VIP ACCESS GRANTED

📦 Plan:
{plan_name}

📅 Expiry:
{expiry.strftime('%d %b %Y')}

🔗 VIP GROUP:
{VIP_LINK}
"""
    )

    context.user_data.clear()

# =========================================
# ADMIN COMMAND
# =========================================

async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message.from_user.id != ADMIN_ID:
        return

    cursor.execute("SELECT COUNT(*) FROM users")

    total = cursor.fetchone()[0]

    await update.message.reply_text(
        f"👥 Total VIP Users: {total}"
    )

# =========================================
# ERROR HANDLER
# =========================================

async def error_handler(update, context):

    logger.error(context.error)

# =========================================
# MAIN
# =========================================

def main():

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(CommandHandler("users", users))

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    app.add_error_handler(error_handler)

    print("BOT STARTED SUCCESSFULLY")

    app.run_polling()

# =========================================
# START BOT
# =========================================

if __name__ == "__main__":
    main()
