import asyncio
import os
import sys
import logging
from api import get_drama_detail, get_all_episodes
from downloader import download_all_episodes
from merge import merge_episodes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DEBUG")

async def test_single_drama(book_id):
    print(f"--- DEBUGGING DRAMA {book_id} ---")
    
    # 1. Cek API
    detail = await get_drama_detail(book_id)
    if not detail:
        print("❌ GAGAL: API tidak memberikan detail drama.")
        return
    
    title = detail.get("title") or "Unknown"
    print(f"TITLE: {title}")
    
    episodes = await get_all_episodes(book_id)
    print(f"EPISODES COUNT: {len(episodes) if episodes else 0}")
    
    if not episodes:
        print("FAIL: No episodes found.")
        return

    # 2. Cek Download (Coba 2 episode saja untuk tes awal)
    test_eps = episodes[:2]
    temp_dir = "test_download"
    os.makedirs(temp_dir, exist_ok=True)
    
    print("WAIT: Testing download for first 2 episodes...")
    success, total = await download_all_episodes(test_eps, temp_dir)
    
    if success > 0:
        print(f"SUCCESS DOWNLOAD: {success}/{total} episodes.")
        
        # 3. Cek Merge
        print("WAIT: Testing merge...")
        merge_success = merge_episodes(temp_dir, "test_merged.mp4")
        if merge_success:
            print("SUCCESS MERGE!")
        else:
            print("FAIL MERGE.")
    else:
        print("FAIL DOWNLOAD. Check FFmpeg connection.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Penggunaan: python3 debug_test.py {bookId}")
    else:
        asyncio.run(test_single_drama(sys.argv[1]))
