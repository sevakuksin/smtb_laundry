import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

load_dotenv()



ADMIN_FILE = 'admins.txt'

# Initialize logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load admin IDs from file
def load_admins():
    try:
        with open(ADMIN_FILE, 'r') as f:
            return set(int(line.strip()) for line in f if line.strip())
    except FileNotFoundError:
        return set()

# Save admin IDs to file
def save_admins(admins):
    with open(ADMIN_FILE, 'w') as f:
        for admin_id in admins:
            f.write(f"{admin_id}\n")

admins = load_admins()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global admins
    user_id = update.effective_user.id

    if update.message.text and update.message.text.lower().strip() == 'admin':
        admins.add(user_id)
        save_admins(admins)
        await update.message.reply_text("You are now an admin and will receive all future messages/photos.")
        return

    # Forward to all admins except the sender
    for admin_id in admins:
        if admin_id == user_id:
            continue
        try:
            if update.message.photo:
                await context.bot.send_photo(chat_id=admin_id, photo=update.message.photo[-1].file_id,
                                             caption=update.message.caption or '')
            else:
                await context.bot.send_message(chat_id=admin_id, text=update.message.text or '')
        except Exception as e:
            logger.error(f"Error sending to {admin_id}: {e}")

async def main():
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set.")

    app = ApplicationBuilder().token(bot_token).build()

    app.add_handler(MessageHandler(filters.ALL, handle_message))

    logger.info("Bot is running...")
    await app.run_polling()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
