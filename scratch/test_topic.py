import asyncio
import os
from telethon import TelegramClient
from dotenv import load_dotenv

load_dotenv()

async def test_topic():
    api_id = int(os.environ['API_ID'])
    api_hash = os.environ['API_HASH']
    bot_token = os.environ['BOT_TOKEN']
    channel_id = int(os.environ['AUTO_CHANNEL'])
    topic_id = int(os.environ['TOPIC_ID'])
    
    print(f"Connecting to test Topic {topic_id} in Channel {channel_id}...")
    client = TelegramClient('test_session', api_id, api_hash)
    await client.start(bot_token=bot_token)
    
    try:
        await client.send_message(channel_id, "🔔 **Bot Connection Test**: Memastikan Topik sudah OPEN.", reply_to=topic_id)
        print("SUCCESS: Topic is OPEN and receiving messages.")
    except Exception as e:
        print(f"FAILED: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(test_topic())
