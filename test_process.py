import asyncio
import logging
import os
import shutil
import tempfile
from api import get_drama_detail, get_all_episodes
from downloader import download_all_episodes
from merge import merge_episodes

# Mocking Telegram client for testing
class MockClient:
    async def send_file(self, *args, **kwargs):
        print(f"Mock: Sending file to {args[0]}")
        return True
    async def send_message(self, *args, **kwargs):
        print(f"Mock: Sending message to {args[0]}: {args[1]}")
        class MockMsg:
            async def edit(self, text): print(f"Mock: Editing msg: {text}")
            async def delete(self): print("Mock: Deleting msg")
        return MockMsg()

async def test_process(book_id):
    logging.basicConfig(level=logging.INFO)
    print(f"Testing process for {book_id}")
    
    detail = await get_drama_detail(book_id)
    episodes = await get_all_episodes(book_id)
    
    if not detail or not episodes:
        print("Failed to get detail or episodes")
        return

    title = detail.get("title", f"Drama_{book_id}")
    temp_dir = tempfile.mkdtemp(prefix=f"test_{book_id}_")
    video_dir = os.path.join(temp_dir, "episodes")
    os.makedirs(video_dir, exist_ok=True)
    
    try:
        print("Starting download...")
        success = await download_all_episodes(episodes[:3], video_dir) # Only test 3 episodes
        print(f"Download success: {success}")
        
        if success:
            print("Starting merge...")
            output_video_path = os.path.join(temp_dir, f"{title}.mp4")
            merge_success = merge_episodes(video_dir, output_video_path)
            print(f"Merge success: {merge_success}")
            
            if merge_success:
                print(f"Output file size: {os.path.getsize(output_video_path)} bytes")
    finally:
        # Keep temp_dir for inspection if needed, or cleanup
        # shutil.rmtree(temp_dir)
        print(f"Temp dir: {temp_dir}")

if __name__ == "__main__":
    import sys
    bid = sys.argv[1] if len(sys.argv) > 1 else "14799"
    asyncio.run(test_process(bid))
