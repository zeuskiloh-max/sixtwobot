from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

TOKEN = "8787667902:AAGmQKmePgm2-pUD25oOwSuGn5mSN9elL0w"

ADMIN_ID = 123456789
GROUP_ID = -1003944904264


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 Bot is now running successfully on Render!"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/start - Start bot\n/help - Help menu"
    )


async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    await update.message.reply_text(
        f"Your User ID: {user_id}\nChat ID: {chat_id}"
    )


def main():
    print("Bot is starting...")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("id", id_command))

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
