import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telethon import TelegramClient
from telethon.sessions import StringSession

BOT_TOKEN = "8051561278:AAEuoYj7g0jtHMwkFhOI6HyibZwTwZcDohA"
OWNER_ID = 849255691  # آیدی عددی خودت

# وضعیت هر کاربر
user_data_store = {}

# ساخت loop برای بعضی محیط‌ها
try:
    asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)


def is_owner(update: Update) -> bool:
    return update.effective_user and update.effective_user.id == OWNER_ID


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        await update.message.reply_text("اجازه دسترسی نداری.")
        return

    user_id = update.effective_user.id
    user_data_store[user_id] = {
        "step": "api_id"
    }

    await update.message.reply_text(
        "سلام.\n"
        "اول API_ID را بفرست."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        await update.message.reply_text("اجازه دسترسی نداری.")
        return

    user_id = update.effective_user.id
    text = update.message.text.strip()

    if user_id not in user_data_store:
        await update.message.reply_text("اول /start را بزن.")
        return

    data = user_data_store[user_id]
    step = data.get("step")

    try:
        if step == "api_id":
            data["api_id"] = int(text)
            data["step"] = "api_hash"
            await update.message.reply_text("خوبه. حالا API_HASH را بفرست.")
            return

        elif step == "api_hash":
            data["api_hash"] = text
            data["step"] = "phone"
            await update.message.reply_text("عالی. حالا شماره را با فرمت +98... بفرست.")
            return

        elif step == "phone":
            data["phone"] = text

            await update.message.reply_text("دارم کد را ارسال می‌کنم...")

            client = TelegramClient(
                StringSession(),
                data["api_id"],
                data["api_hash"]
            )

            await client.connect()
            result = await client.send_code_request(data["phone"])

            data["client"] = client
            data["phone_code_hash"] = result.phone_code_hash
            data["step"] = "code"

            await update.message.reply_text(
                "کد به تلگرام ارسال شد.\n"
                "حالا کد را بفرست."
            )
            return

        elif step == "code":
            code = text
            client = data["client"]

            await client.sign_in(
                phone=data["phone"],
                code=code,
                phone_code_hash=data["phone_code_hash"]
            )

            session = client.session.save()

            await update.message.reply_text(
                "✅ لاگین موفق.\n\n"
                f"StringSession:\n`{session}`",
                parse_mode="Markdown"
            )

            await client.disconnect()

            data["step"] = "done"
            return

        else:
            await update.message.reply_text("کار تمام شده. اگر از اول می‌خواهی، /start را بزن.")

    except Exception as e:
        await update.message.reply_text(f"❌ خطا:\n{e}")


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
