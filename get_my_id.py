# get_my_id.py
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from config import TELEGRAM_TOKEN

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    
    response = (
        f"👤 *Ձեր տվյալները*\n\n"
        f"• **Chat ID:** `{chat.id}`\n"
        f"• **User ID:** `{user.id}`\n"
        f"• **Անուն:** {user.full_name}\n\n"
        f"📝 *Օգտագործեք այս Chat ID-ն օպերատորի համար:*\n"
        f"`OPERATOR_CHAT_ID = {chat.id}`"
    )
    
    await update.message.reply_text(response, parse_mode='Markdown')
    
    # Also print to console
    print(f"\n{'='*50}")
    print(f"👤 User: {user.full_name}")
    print(f"🆔 User ID: {user.id}")
    print(f"💬 Chat ID: {chat.id}")
    print(f"📊 Chat type: {chat.type}")
    print(f"{'='*50}\n")

async def main():
    """Main function for v20.x"""
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    
    print("🤖 Send /start to this bot to get your Chat ID")
    
    # Start the bot
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    # Keep running
    try:
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        pass
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()

if __name__ == "__main__":
    asyncio.run(main())