import asyncio
import os
from telethon import TelegramClient
from dotenv import load_dotenv

load_dotenv()

async def test():
    api_id = int(os.getenv("API_ID"))
    api_hash = os.getenv("API_HASH")
    bot_token = os.getenv("BOT_TOKEN")
    channel_id = int(os.getenv("AUTO_CHANNEL"))
    
    print(f"Testing with Channel ID: {channel_id}")
    
    client = TelegramClient('test_channel_session', api_id, api_hash)
    await client.start(bot_token=bot_token)
    try:
        await client.send_message(channel_id, "🔔 **Test Message from DramaBite Bot**\n\nJika Anda melihat pesan ini, berarti Channel ID sudah benar dan bot memiliki akses.")
        print("✅ SUCCESS: Message sent to channel.")
    except Exception as e:
        print(f"❌ FAILURE: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(test())
