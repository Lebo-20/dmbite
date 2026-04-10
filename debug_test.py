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
    print(f"✅ Judul: {title}")
    
    episodes = await get_all_episodes(book_id)
    print(f"✅ Jumlah Episode: {len(episodes) if episodes else 0}")
    
    if not episodes:
        print("❌ GAGAL: Tidak ada episode.")
        return

    # 2. Cek Download (Coba 2 episode saja untuk tes awal)
    test_eps = episodes[:2]
    temp_dir = "test_download"
    os.makedirs(temp_dir, exist_ok=True)
    
    print("⏳ Mengetes download 2 episode pertama...")
    success, total = await download_all_episodes(test_eps, temp_dir)
    
    if success > 0:
        print(f"✅ BERHASIL DOWNLOAD: {success}/{total} episode.")
        
        # 3. Cek Merge
        print("⏳ Mengetes merge...")
        merge_success = merge_episodes(temp_dir, "test_merged.mp4")
        if merge_success:
            print("✅ BERHASIL MERGE!")
        else:
            print("❌ GAGAL MERGE.")
    else:
        print("❌ GAGAL DOWNLOAD. Cek koneksi FFmpeg Anda.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Penggunaan: python3 debug_test.py {bookId}")
    else:
        asyncio.run(test_single_drama(sys.argv[1]))
