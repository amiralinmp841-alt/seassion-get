import os
from telethon import TelegramClient
from telethon.sessions import StringSession

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
PHONE = os.environ["PHONE"]
CODE = os.environ["CODE"]

client = TelegramClient(StringSession(), API_ID, API_HASH)

async def main():
    await client.connect()

    if not await client.is_user_authorized():
        await client.send_code_request(PHONE)
        await client.sign_in(PHONE, CODE)

    print(client.session.save())

with client:
    client.loop.run_until_complete(main())
