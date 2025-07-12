import os
import logging
import asyncio
import nest_asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ✅ Load environment variables from .env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

# ✅ Get token from environment
bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
if not bot_token:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN not set in .env file or environment.")

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ADMIN_FILE = 'admins.txt'

# Load and save admin utilities
def load_admins():
    try:
        with open(ADMIN_FILE, 'r') as f:
            return set(int(line.strip()) for line in f if line.strip())
    except FileNotFoundError:
        return set()

def save_admins(admins):
    with open(ADMIN_FILE, 'w') as f:
        for admin_id in admins:
            f.write(f"{admin_id}\n")

def load_users():
    users = {}
    try:
        with open('users.txt', 'r') as f:
            for line in f:
                if line.strip():
                    user_id, name = line.split(':', 1)
                    users[int(user_id.strip())] = name.strip()
    except FileNotFoundError:
        pass
    return users

def save_users(users):
    with open('users.txt', 'w') as f:
        for user_id in users.keys():
            f.write(f"{user_id}: {users[user_id]}\n")

admins = load_admins()
users = load_users()


# /start handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hello!\n\n"
        "All your further messages/photos will be sent to manager who can unlock the laundry machines.\n"
        "Please send the 4-digit number under the QR Kaspicode on the machine here."
        "\n\n"
        "Now you need to write the washing machine number + the gel you used when you wash.\n"
        "Also, you can use the dryer too!\n\n"
        "Привет!\n\n"
        "Все твои дальнейшие сообщения/фото будут отправлены менеджеру, который может разблокировать стиральные машины.\n"
        "Пожалуйста, отправь сюда 4-значный номер под QR Kaspicode на машинке.\n\n"
        "Теперь все должны указывать номер машинки + используемый гель, когда стирают.\n"
        "И ещё: сушилкой тоже можно пользоваться!\n\n",
        parse_mode='Markdown'
    )

# Forwarding handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global admins
    global users
    user_id = update.effective_user.id
    if user_id not in users and user_id not in admins:
        users[user_id] = 0
        save_users(users)

    if update.message.text and update.message.text.lower().strip() == 'i am the manager':
        admins.add(user_id)
        save_admins(admins)
        await update.message.reply_text("✅ You will now receive all future messages/photos from students.")
        return

    if update.message.text.lower().strip() == 'i am not the manager':
        if user_id in admins:
            admins.remove(user_id)
            save_admins(admins)
            await update.message.reply_text("🛑 You are no longer an admin.")
        else:
            await update.message.reply_text("ℹ️ You are not an admin.")
        return

    # check if users[user_id] is 0, if so, send a welcome message and set it to 1
    # message: "👋 Hi! We have updated the bot. Please note:
    #
    # From now on, you need to write the washing machine number + the gel you used when you wash.
    #
    # Also, you can use the dryer too!
    #
    # Привет! Мы обновили бота. Пожалуйста, учти:
    #
    # Теперь все должны указывать номер машинки + используемый гель, когда стирают.
    #
    # И ещё: сушилкой тоже можно пользоваться!

    if users[user_id] == 0:
        await update.message.reply_text(
            "👋 Hi! We have updated the bot. Please note:\n\n"
            "From now on, you need to write the washing machine number + the gel you used when you wash.\n\n"
            "Also, you can use the dryer too! \nThis message won't be repeated, please use /start to view it again. \n\n"
            "Привет! Мы обновили бота. Пожалуйста, учти:\n\n"
            "Теперь все должны указывать номер машинки + используемый гель, когда стирают.\n\n"
            "И ещё: сушилкой тоже можно пользоваться! \n Это сообщение не будет повторяться, пожалуйста, используй /start чтобы увидеть его снова."
        )
        users[user_id] = 1
        save_users(users)

    forwarded = False  # track if sent to at least one admin

    for admin_id in admins:
        if admin_id == user_id:
            continue
        try:
            if update.message.photo:
                await context.bot.send_photo(
                    chat_id=admin_id,
                    photo=update.message.photo[-1].file_id,
                    caption=update.message.caption or f"Forwarded from {update.effective_user.first_name}"
                )
            else:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=f"Forwarded from {update.effective_user.first_name}:\n{update.message.text or ''}"
                )
            forwarded = True
        except Exception as e:
            logger.error(f"Error sending to {admin_id}: {e}")

    if forwarded:
        await update.message.reply_text("✅ Your message has been sent to the manager.")


# Main app runner
async def main():
    logger.info("✅ Bot is starting...")
    app = ApplicationBuilder().token(bot_token).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.ALL, handle_message))

    await app.run_polling()

# Safe event loop handling across environments
if __name__ == '__main__':
    import sys
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        asyncio.run(main())
    except RuntimeError:
        # If already running event loop (notebooks, VSCode interactive)
        nest_asyncio.apply()
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())

