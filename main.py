import os
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
PHONE = os.environ["PHONE"]
CODE = os.environ.get("CODE")  # ممکنه هنوز در ابتدا خالی باشه

# ✅ ایجاد loop به صورت دستی برای Python 3.12+
try:
    asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

client = TelegramClient(StringSession(), API_ID, API_HASH)

async def main():
    await client.connect()

    if not await client.is_user_authorized():
        print("📨 Sending code request...")
        await client.send_code_request(PHONE)
        print("✅ Code sent. Please set CODE in Render and redeploy.")
        if not CODE:
            return
        await client.sign_in(PHONE, CODE)

    print("✅ LOGGED IN as", (await client.get_me()).first_name)
    print("\n👇 YOUR STRING SESSION:")
    print(client.session.save())

if __name__ == "__main__":
    client.loop.run_until_complete(main())
