from telegram import (
    Update,
    ReplyKeyboardMarkup
)

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

from datetime import datetime, timedelta
import sqlite3
import asyncio
import requests

# ====================================
# TELEGRAM CONFIG
# ====================================

TOKEN = "8787667902:AAEj_2bxGPjBiH5hi2rGem1XgD1FuQxhrO0"

ADMIN_ID = 7355302122

GROUP_ID = -1003944904264

GROUP_LINK = "https://t.me/+z0zKkLWDdps4OGQ0"

# ====================================
# PAYHERO CONFIG
# ====================================

API_USERNAME = "cT1F4Py83BsCQVx5H0Fs"

API_PASSWORD = "bWVYoV5SbWts5kwLr5Y40TewMqYRpWnDpvGTZEPX"

CHANNEL_ID = 8506

# ====================================
# DATABASE
# ====================================

conn = sqlite3.connect(
    "vip.db",
    check_same_thread=False
)

cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS members (
    user_id INTEGER,
    expiry TEXT
)
""")

conn.commit()

# ====================================
# PLANS
# ====================================

PLANS = {

    "daily": {
        "price": 50,
        "days": 1
    },

    "basic": {
        "price": 200,
        "days": 7
    },

    "standard": {
        "price": 500,
        "days": 30
    },

    "premium": {
        "price": 1200,
        "days": 90
    }

}

# ====================================
# START
# ====================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    keyboard = [

        ["📅 Daily"],

        ["⭐ Basic"],

        ["🔥 Standard"],

        ["👑 Premium"],

        ["♻️ Renew Subscription"],

        ["⏳ My Subscription"],

        ["📞 Support"]

    ]

    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True
    )

    await update.message.reply_text(
        "🔥 Welcome To VIP Membership 🔥",
        reply_markup=reply_markup
    )

    await asyncio.sleep(1)

    await update.message.reply_text(
        "Choose a package below 👇"
    )

# ====================================
# HANDLE MESSAGE
# ====================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text
    user_id = update.message.from_user.id

    # DAILY

    if text == "📅 Daily":

        context.user_data["plan"] = "daily"

        await update.message.reply_text(
            """
📅 DAILY PLAN

💰 Price: KES 50
⏳ Duration: 1 Day

Send your M-PESA number.

Example:
0712345678
"""
        )

        return

    # BASIC

    elif text == "⭐ Basic":

        context.user_data["plan"] = "basic"

        await update.message.reply_text(
            """
⭐ BASIC PLAN

💰 Price: KES 200
⏳ Duration: 7 Days

Send your M-PESA number.
"""
        )

        return

    # STANDARD

    elif text == "🔥 Standard":

        context.user_data["plan"] = "standard"

        await update.message.reply_text(
            """
🔥 STANDARD PLAN

💰 Price: KES 500
⏳ Duration: 30 Days

Send your M-PESA number.
"""
        )

        return

    # PREMIUM

    elif text == "👑 Premium":

        context.user_data["plan"] = "premium"

        await update.message.reply_text(
            """
👑 PREMIUM PLAN

💰 Price: KES 1200
⏳ Duration: 90 Days

Send your M-PESA number.
"""
        )

        return

    # RENEW

    elif text == "♻️ Renew Subscription":

        await update.message.reply_text(
            "Choose a package again to renew."
        )

        return

    # MY SUBSCRIPTION

    elif text == "⏳ My Subscription":

        cur.execute(
            "SELECT expiry FROM members WHERE user_id=?",
            (user_id,)
        )

        result = cur.fetchone()

        if not result:

            await update.message.reply_text(
                "❌ No active subscription."
            )

            return

        expiry = datetime.fromisoformat(result[0])

        remaining = expiry - datetime.now()

        days = remaining.days

        if days < 0:

            await update.message.reply_text(
                "❌ Subscription expired."
            )

        else:

            await update.message.reply_text(
                f"""
✅ ACTIVE SUBSCRIPTION

⏳ Remaining:
{days} day(s)
"""
            )

        return

    # SUPPORT

    elif text == "📞 Support":

        await update.message.reply_text(
            "Contact admin for support."
        )

        return

    # PHONE NUMBER

    if "plan" not in context.user_data:
        return

    phone = text.strip()

    plan = context.user_data["plan"]

    amount = PLANS[plan]["price"]

    days = PLANS[plan]["days"]

    await update.message.reply_text(
        "⏳ Sending M-PESA prompt..."
    )

    success = stk_push(phone, amount)

    if success:

        await update.message.reply_text(
            "✅ STK Push sent successfully.\nComplete payment on your phone."
        )

        await asyncio.sleep(15)

        expiry = datetime.now() + timedelta(days=days)

        cur.execute(
            "DELETE FROM members WHERE user_id=?",
            (user_id,)
        )

        cur.execute(
            "INSERT INTO members VALUES (?, ?)",
            (
                user_id,
                expiry.isoformat()
            )
        )

        conn.commit()

        invite = await context.bot.create_chat_invite_link(
            chat_id=GROUP_ID,
            member_limit=1
        )

        await update.message.reply_text(
            f"""
✅ PAYMENT CONFIRMED

🎉 VIP Access Granted

🔗 Your One-Time VIP Link:

{invite.invite_link}

⚠️ Link works once only.
"""
        )

    else:

        await update.message.reply_text(
            "❌ Failed to send STK Push."
        )

# ====================================
# STK PUSH
# ====================================

def stk_push(phone, amount):

    url = "https://backend.payhero.co.ke/api/v2/payments"

    payload = {

        "phone_number": phone,

        "channel_id": CHANNEL_ID,

        "amount": amount,

        "provider": "m-pesa"

    }

    headers = {
        "Content-Type": "application/json"
    }

    try:

        response = requests.post(
            url,
            json=payload,
            headers=headers,
            auth=(API_USERNAME, API_PASSWORD)
        )

        print(response.text)

        # UPDATED SUCCESS CHECK

        if response.status_code in [200, 201, 202]:

            return True

        return False

    except Exception as e:

        print(e)

        return False

# ====================================
# REMOVE EXPIRED USERS
# ====================================

async def remove_expired(context: ContextTypes.DEFAULT_TYPE):

    cur.execute(
        "SELECT user_id, expiry FROM members"
    )

    rows = cur.fetchall()

    now = datetime.now()

    for user_id, expiry in rows:

        expiry_date = datetime.fromisoformat(expiry)

        if now > expiry_date:

            try:

                await context.bot.ban_chat_member(
                    GROUP_ID,
                    user_id
                )

                await context.bot.unban_chat_member(
                    GROUP_ID,
                    user_id
                )

            except:
                pass

            cur.execute(
                "DELETE FROM members WHERE user_id=?",
                (user_id,)
            )

            conn.commit()

# ====================================
# WELCOME MESSAGE
# ====================================

async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):

    for member in update.message.new_chat_members:

        await update.message.reply_text(
            f"""
🔥 Welcome {member.first_name}

Enjoy your VIP access 🎉
"""
        )

# ====================================
# BROADCAST
# ====================================

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message.from_user.id != ADMIN_ID:
        return

    if not context.args:

        await update.message.reply_text(
            "Usage:\n/broadcast your message"
        )

        return

    message = " ".join(context.args)

    cur.execute("SELECT user_id FROM members")

    users = cur.fetchall()

    count = 0

    for user in users:

        try:

            await context.bot.send_message(
                chat_id=user[0],
                text=message
            )

            count += 1

        except:
            pass

    await update.message.reply_text(
        f"✅ Broadcast sent to {count} users."
    )

# ====================================
# USERS
# ====================================

async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message.from_user.id != ADMIN_ID:
        return

    cur.execute("SELECT * FROM members")

    users = cur.fetchall()

    await update.message.reply_text(
        f"👥 Total Active Users: {len(users)}"
    )

# ====================================
# MAIN
# ====================================

def main():

    app = Application.builder().token(TOKEN).build()

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("broadcast", broadcast)
    )

    app.add_handler(
        CommandHandler("users", users)
    )

    app.add_handler(
        MessageHandler(
            filters.StatusUpdate.NEW_CHAT_MEMBERS,
            welcome
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    app.job_queue.run_repeating(
        remove_expired,
        interval=60
    )

    print("Bot running...")

    app.run_polling()

# ====================================

if __name__ == "__main__":
    main()
