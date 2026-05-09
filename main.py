import os
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
from telethon.errors.rpcerrorlist import (
    PhoneCodeInvalidError,
    SessionPasswordNeededError,
    FloodWaitError,
)

# --- تنظیمات ---
BOT_TOKEN = "8778171198:AAHylKaETHLzmBNNq5LzOBLNcIjUPLu_-Sc"  # توکن ربات خودت را اینجا بگذار
OWNER_ID = 849255691  # آیدی عددی خودت را اینجا بگذار
# --- تنظیمات ---

# وضعیت هر کاربر (برای نگهداری داده‌ها در طول مکالمه)
# {user_id: {"step": "...", "api_id": ..., "api_hash": ..., "phone": ..., "phone_code_hash": ..., "client": TelethonClient}}
user_data_store = {}

# ایجاد loop برای محیط‌های خاص (مثل Render)
try:
    asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

def is_owner(update: Update) -> bool:
    """چک می‌کند که آیا کاربر فرستنده پیام، مالک ربات است یا خیر."""
    return update.effective_user and update.effective_user.id == OWNER_ID

async def send_to_owner(context: ContextTypes.DEFAULT_TYPE, text: str):
    """پیام را به مالک ربات می‌فرستد."""
    await context.bot.send_message(chat_id=OWNER_ID, text=text)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /start برای شروع فرآیند لاگین."""
    if not is_owner(update):
        await update.message.reply_text("شما اجازه دسترسی به این ربات را ندارید.")
        return

    user_id = update.effective_user.id
    user_data_store[user_id] = {
        "step": "api_id",
        "api_id": None,
        "api_hash": None,
        "phone": None,
        "phone_code_hash": None,
        "client": None,
    }

    await update.message.reply_text(
        "سلام! برای ساخت String Session، لطفا مراحل زیر را دنبال کنید:\n\n"
        "1. **API ID** خود را بفرستید.\n"
        "(می‌توانید از @userinfobot یا وبسایت my.telegram.org دریافت کنید)"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پیام‌های متنی کاربر را پردازش می‌کند."""
    if not is_owner(update):
        await update.message.reply_text("شما اجازه دسترسی به این ربات را ندارید.")
        return

    user_id = update.effective_user.id
    text = update.message.text.strip()

    if user_id not in user_data_store or user_data_store[user_id]["step"] == "done":
        await update.message.reply_text("لطفا اول /start را بزنید تا فرآیند شروع شود.")
        return

    data = user_data_store[user_id]
    step = data.get("step")

    try:
        if step == "api_id":
            try:
                data["api_id"] = int(text)
                data["step"] = "api_hash"
                await update.message.reply_text(
                    "2. **API Hash** خود را بفرستید."
                )
            except ValueError:
                await update.message.reply_text("❌ خطا: API ID باید یک عدد باشد. لطفا دوباره امتحان کنید.")

        elif step == "api_hash":
            data["api_hash"] = text
            data["step"] = "phone"
            await update.message.reply_text(
                "3. **شماره تلفن** خود را با فرمت بین‌المللی (مثلا: +989123456789) بفرستید."
            )

        elif step == "phone":
            data["phone"] = text
            await update.message.reply_text("در حال اتصال به تلگرام و ارسال کد...")

            # اتصال با Telethon
            client = TelegramClient(
                StringSession(),
                data["api_id"],
                data["api_hash"]
            )
            await client.connect()

            # اگر قبلا لاگین شده باشد، session را ذخیره کن
            if await client.is_user_authorized():
                session_string = client.session.save()
                await update.message.reply_text(
                    "✅ شما قبلا لاگین شده‌اید.\n\n"
                    f"**String Session شما:**\n`{session_string}`",
                    parse_mode="Markdown"
                )
                await client.disconnect()
                data["step"] = "done"
                return

            # ارسال درخواست کد
            send_code_result = await client.send_code_request(data["phone"])
            data["client"] = client
            data["phone_code_hash"] = send_code_result.phone_code_hash
            data["step"] = "code"

            await update.message.reply_text(
                "4. کدی که از تلگرام دریافت کردید را اینجا بفرستید."
            )
            await send_to_owner(context, f"کد برای {data['phone']} ارسال شد. منتظر دریافت کد...")

        elif step == "code":
            code = text
            client = data["client"]
            phone_code_hash = data["phone_code_hash"]

            try:
                await update.message.reply_text("در حال ورود با کد...")
                # تلاش برای ورود با کد
                await client.sign_in(
                    phone=data["phone"],
                    code=code,
                    phone_code_hash=phone_code_hash
                )

                # اگر اینجا برسد یعنی کد درست بوده و نیازی به پسورد نیست
                session_string = client.session.save()
                await update.message.reply_text(
                    "✅ لاگین موفقیت آمیز بود!\n\n"
                    f"**String Session شما:**\n`{session_string}`",
                    parse_mode="Markdown"
                )
                await send_to_owner(context, f"✅ لاگین موفق برای {data['phone']}. Session ساخته شد.")
                data["step"] = "done"
                await client.disconnect()

            except SessionPasswordNeededError:
                data["step"] = "password"
                await update.message.reply_text(
                    "5. حساب شما تأیید دو مرحله‌ای (Two-Step Verification) دارد.\n"
                    "**رمز عبور (Password)** حساب تلگرام خود را بفرستید."
                )
                await send_to_owner(context, f"حساب {data['phone']} نیاز به رمز عبور دارد.")

            except FloodWaitError as e:
                await update.message.reply_text(f"❌ خطا: تعداد درخواست‌ها زیاد است. {e.seconds} ثانیه صبر کنید.")
                await send_to_owner(context, f"❌ FloodWaitError برای {data['phone']}: {e.seconds} ثانیه.")
                # اینجا می‌توانید sleep کنید یا دوباره تلاش کنید

            except PhoneCodeInvalidError:
                await update.message.reply_text("❌ خطا: کد وارد شده نامعتبر است. لطفا دوباره امتحان کنید.")
                await send_to_owner(context, f"❌ PhoneCodeInvalidError برای {data['phone']}.")

            except Exception as e:
                await update.message.reply_text(f"❌ یک خطای ناشناخته رخ داد:\n`{e}`")
                await send_to_owner(context, f"❌ خطای ناشناخته در مرحله code برای {data['phone']}:\n`{e}`")
                # ریست کردن داده‌ها برای شروع مجدد
                user_data_store.pop(user_id, None)


        elif step == "password":
            password = text
            client = data["client"]

            try:
                await update.message.reply_text("در حال ورود با رمز عبور...")
                # ورود با رمز عبور
                await client.sign_in(password=password)

                session_string = client.session.save()
                await update.message.reply_text(
                    "✅ لاگین موفقیت آمیز بود!\n\n"
                    f"**String Session شما:**\n`{session_string}`",
                    parse_mode="Markdown"
                )
                await send_to_owner(context, f"✅ لاگین موفق (با رمز عبور) برای {data['phone']}. Session ساخته شد.")
                data["step"] = "done"
                await client.disconnect()

            except FloodWaitError as e:
                await update.message.reply_text(f"❌ خطا: تعداد درخواست‌ها زیاد است. {e.seconds} ثانیه صبر کنید.")
                await send_to_owner(context, f"❌ FloodWaitError در مرحله password برای {data['phone']}: {e.seconds} ثانیه.")

            except Exception as e:
                await update.message.reply_text(f"❌ خطا در ورود با رمز عبور:\n`{e}`\n\n"
                                             "لطفا دوباره /start را بزنید و امتحان کنید.")
                await send_to_owner(context, f"❌ خطای ورود با رمز عبور برای {data['phone']}:\n`{e}`")
                # ریست کردن داده‌ها برای شروع مجدد
                user_data_store.pop(user_id, None)

    except Exception as e:
        error_message = f"❌ یک خطای کلی در پردازش پیام رخ داد:\n`{e}`"
        await update.message.reply_text(error_message)
        await send_to_owner(context, f"❌ خطای کلی در پردازش پیام از {user_id}:\n`{e}`")
        # در صورت بروز خطای غیرمنتظره، داده‌ها را پاک کن
        user_data_store.pop(user_id, None)


def main():
    """تابع اصلی برای راه‌اندازی ربات."""
    # ساخت Application
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # اضافه کردن هندلرها
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🚀 ربات شروع به کار کرد! منتظر دستور /start...")
    # اجرای ربات
    application.run_polling()


if __name__ == "__main__":
    main()
