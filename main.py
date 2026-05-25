import os
import sqlite3
import asyncio
import logging
from datetime import datetime, timedelta

import requests
from telegram import Update, ReplyKeyboardMarkup
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

GROUP_LINK = "https://t.me/+z0zKkLWDdps4OGQ0"

# =========================================
# PAYHERO CONFIG
# =========================================

API_USERNAME = "cT1F4Py83BsCQVx5H0Fs"

API_PASSWORD = "bWVYoV5SbWts5kwLr5Y40TewMqYRpWnDpvGTZEPX"

CHANNEL_ID = 8506

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

conn = sqlite3.connect("vip.db", check_same_thread=False)
cur = conn.cursor()

cur.execute(
    """
CREATE TABLE IF NOT EXISTS members (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    full_name TEXT,
    plan TEXT,
    expiry TEXT,
    joined_at TEXT
)
"""
)

conn.commit()

# =========================================
# PLANS
# =========================================

PLANS = {
    "daily": {
        "name": "📅 Daily",
        "price": 50,
        "days": 1,
    },
    "basic": {
        "name": "⭐ Basic",
        "price": 200,
        "days": 7,
    },
    "standard": {
        "name": "🔥 Standard",
        "price": 500,
        "days": 30,
    },
    "premium": {
        "name": "👑 Premium",
        "price": 1200,
        "days": 90,
    },
}

# =========================================
# KEYBOARD
# =========================================

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["📅 Daily", "⭐ Basic"],
        ["🔥 Standard", "👑 Premium"],
        ["⏳ My Subscription", "♻️ Renew"],
        ["👥 Total Users", "📞 Support"],
    ],
    resize_keyboard=True,
)

# =========================================
# UTILITIES
# =========================================


def valid_phone(phone: str):
    return (
        phone.startswith("07")
        and len(phone) == 10
        and phone.isdigit()
    )


async def send_main_menu(message):
    await message.reply_text(
        "🔥 Welcome To VIP Membership 🔥\n\nChoose a package below 👇",
        reply_markup=MAIN_KEYBOARD,
    )


# =========================================
# START
# =========================================


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_main_menu(update.message)


# =========================================
# SUBSCRIPTION STATUS
# =========================================


async def subscription_status(update: Update):
    user_id = update.message.from_user.id

    cur.execute(
        "SELECT plan, expiry FROM members WHERE user_id=?",
        (user_id,),
    )

    result = cur.fetchone()

    if not result:
        await update.message.reply_text(
            "❌ You do not have an active subscription."
        )
        return

    plan, expiry = result

    expiry_date = datetime.fromisoformat(expiry)

    remaining = expiry_date - datetime.now()

    if remaining.total_seconds() <= 0:
        await update.message.reply_text(
            "❌ Your subscription has expired."
        )
        return

    await update.message.reply_text(
        f"""
✅ ACTIVE SUBSCRIPTION

📦 Plan: {plan.title()}
⏳ Remaining: {remaining.days} day(s)
📅 Expiry: {expiry_date.strftime('%d %b %Y %I:%M %p')}
"""
    )


# =========================================
# STK PUSH
# =========================================


async def stk_push(phone, amount):
    url = "https://backend.payhero.co.ke/api/v2/payments"

    payload = {
        "phone_number": phone,
        "channel_id": CHANNEL_ID,
        "amount": amount,
        "provider": "m-pesa",
    }

    headers = {
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            auth=(API_USERNAME, API_PASSWORD),
            timeout=30,
        )

        logger.info(response.text)

        if response.status_code in [200, 201, 202]:
            return True

        return False

    except Exception as e:
        logger.error(f"STK PUSH ERROR: {e}")
        return False


# =========================================
# GRANT ACCESS
# =========================================


async def grant_access(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    plan_key,
):
    user = update.message.from_user

    days = PLANS[plan_key]["days"]

    expiry = datetime.now() + timedelta(days=days)

    cur.execute(
        """
        REPLACE INTO members
        (user_id, username, full_name, plan, expiry, joined_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """,
        (
            user.id,
            user.username,
            user.full_name,
            plan_key,
            expiry.isoformat(),
            datetime.now().isoformat(),
        ),
    )

    conn.commit()

    invite = await context.bot.create_chat_invite_link(
        chat_id=GROUP_ID,
        member_limit=1,
    )

    await update.message.reply_text(
        f"""
✅ PAYMENT CONFIRMED

🎉 VIP Access Granted

📦 Plan: {PLANS[plan_key]['name']}
📅 Expires: {expiry.strftime('%d %b %Y')}

🔗 VIP Link:
{invite.invite_link}

⚠️ Link works once only.
"""
    )


# =========================================
# HANDLE MESSAGES
# =========================================


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    plan_buttons = {
        "📅 Daily": "daily",
        "⭐ Basic": "basic",
        "🔥 Standard": "standard",
        "👑 Premium": "premium",
    }

    if text in plan_buttons:
        plan_key = plan_buttons[text]

        context.user_data["selected_plan"] = plan_key

        plan = PLANS[plan_key]

        await update.message.reply_text(
            f"""
{plan['name']} PLAN

💰 Price: KES {plan['price']}
⏳ Duration: {plan['days']} day(s)

📲 Send your M-PESA number.

Example:
0712345678
"""
        )

        return

    if text == "⏳ My Subscription":
        await subscription_status(update)
        return

    if text == "♻️ Renew":
        await update.message.reply_text(
            "Choose another plan to renew your subscription."
        )
        return

    if text == "👥 Total Users":
        cur.execute("SELECT COUNT(*) FROM members")
        total = cur.fetchone()[0]

        await update.message.reply_text(
            f"👥 Active VIP Users: {total}"
        )
        return

    if text == "📞 Support":
        await update.message.reply_text(
            "📞 Contact Admin for assistance."
        )
        return

    if "selected_plan" not in context.user_data:
        return

    phone = text.strip()

    if not valid_phone(phone):
        await update.message.reply_text(
            "❌ Invalid phone number.\n\nUse format:\n0712345678"
        )
        return

    plan_key = context.user_data["selected_plan"]

    amount = PLANS[plan_key]["price"]

    await update.message.reply_text(
        "⏳ Sending M-PESA STK Push..."
    )

    success = await stk_push(phone, amount)

    if not success:
        await update.message.reply_text(
            "❌ Failed to send STK Push.\nTry again later."
        )
        return

    await update.message.reply_text(
        "✅ STK Push sent successfully.\n\nComplete payment on your phone."
    )

    await asyncio.sleep(15)

    await grant_access(update, context, plan_key)

    context.user_data.clear()


# =========================================
# REMOVE EXPIRED USERS
# =========================================


async def remove_expired(context: ContextTypes.DEFAULT_TYPE):
    cur.execute(
        "SELECT user_id, expiry FROM members"
    )

    users = cur.fetchall()

    now = datetime.now()

    for user_id, expiry in users:
        expiry_date = datetime.fromisoformat(expiry)

        if now > expiry_date:
            try:
                await context.bot.ban_chat_member(
                    GROUP_ID,
                    user_id,
                )

                await context.bot.unban_chat_member(
                    GROUP_ID,
                    user_id,
                )

                cur.execute(
                    "DELETE FROM members WHERE user_id=?",
                    (user_id,),
                )

                conn.commit()

                logger.info(f"Removed expired user {user_id}")

            except Exception as e:
                logger.error(f"REMOVE ERROR: {e}")


# =========================================
# WELCOME USERS
# =========================================


async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        await update.message.reply_text(
            f"🔥 Welcome {member.first_name}!\n\nEnjoy your VIP access 🎉"
        )


# =========================================
# BROADCAST
# =========================================


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

    success = 0
    failed = 0

    for user in users:
        try:
            await context.bot.send_message(
                chat_id=user[0],
                text=message,
            )

            success += 1

        except Exception as e:
            logger.error(f"BROADCAST ERROR: {e}")
            failed += 1

    await update.message.reply_text(
        f"""
✅ Broadcast Complete

✔️ Sent: {success}
❌ Failed: {failed}
"""
    )


# =========================================
# USERS COMMAND
# =========================================


async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    cur.execute("SELECT * FROM members")

    total = len(cur.fetchall())

    await update.message.reply_text(
        f"👥 Total Active VIP Users: {total}"
    )


# =========================================
# ERROR HANDLER
# =========================================


async def error_handler(update, context):
    logger.error(msg="Exception while handling update:", exc_info=context.error)


# =========================================
# MAIN
# =========================================


def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("users", users))

    app.add_handler(
        MessageHandler(
            filters.StatusUpdate.NEW_CHAT_MEMBERS,
            welcome,
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message,
        )
    )

    app.job_queue.run_repeating(
        remove_expired,
        interval=60,
        first=10,
    )

    app.add_error_handler(error_handler)

    logger.info("Bot started successfully...")

    app.run_polling(drop_pending_updates=True)


# =========================================
# START BOT
# =========================================

if __name__ == "__main__":
    main()
