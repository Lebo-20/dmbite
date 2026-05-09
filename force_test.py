import asyncio
import os
import sys

# Ensure UTF-8 output for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from main import process_drama_full, client, BotState
from dotenv import load_dotenv

load_dotenv()

async def run_test():
    print("Starting forced test for drama 10960...")
    # Bypass the "is_processing" check
    BotState.is_processing = True
    
    try:
        # Start client
        await client.connect()
        if not await client.is_user_authorized():
            print("Client not authorized. Make sure you have a valid session.")
            return

        admin_id = int(os.environ.get("ADMIN_ID", 0))
        auto_channel = int(os.environ.get("AUTO_CHANNEL", admin_id))
        topic_id = os.environ.get("TOPIC_ID", "0")
        
        # Normalize topic_id
        if not topic_id or topic_id == "0":
            topic_id = None
        else:
            topic_id = int(topic_id)

        print(f"Target Channel: {auto_channel}, Topic: {topic_id}")
        
        # Force process 
        success = await process_drama_full(
            '10960', 
            admin_id, 
            target_chat=auto_channel, 
            target_topic=topic_id
        )
        
        if success:
            print("Test completed successfully!")
        else:
            print("Test failed. Check logs for details.")
            
    finally:
        BotState.is_processing = False
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(run_test())
