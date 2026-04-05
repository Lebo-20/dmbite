import os
import asyncio
import logging
import shutil
import tempfile
import random
from telethon import TelegramClient, events, Button
from dotenv import load_dotenv

load_dotenv()

# Local imports
from api import (
    get_drama_detail, get_all_episodes, get_latest_dramas,
    get_home_dramas, search_dramas
)
from downloader import download_all_episodes
from merge import merge_episodes
from uploader import upload_drama

# Configuration
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
AUTO_CHANNEL = int(os.environ.get("AUTO_CHANNEL", ADMIN_ID))
PROCESSED_FILE = "processed.json"

# ... rest of the state management remains same ...
def load_processed():
    if os.path.exists(PROCESSED_FILE):
        import json
        with open(PROCESSED_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_processed(data):
    import json
    with open(PROCESSED_FILE, "w") as f:
        json.dump(list(data), f)

processed_ids = load_processed()

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Bot State
class BotState:
    is_auto_running = True
    is_processing = False

# Initialize client
client = TelegramClient('dramabite_bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

def get_panel_buttons():
    status_text = "🟢 RUNNING" if BotState.is_auto_running else "🔴 STOPPED"
    return [
        [Button.inline("▶️ Start Auto", b"start_auto"), Button.inline("⏹ Stop Auto", b"stop_auto")],
        [Button.inline(f"📊 Status: {status_text}", b"status")]
    ]

# ... Panel handlers are ok ...
@client.on(events.NewMessage(pattern='/update'))
async def update_bot(event):
    if event.sender_id != ADMIN_ID:
        return
    import subprocess
    import sys
    
    status_msg = await event.reply("🔄 Menarik pembaruan dari GitHub...")
    try:
        # Run git pull
        result = subprocess.run(["git", "pull", "origin", "main"], capture_output=True, text=True)
        await status_msg.edit(f"✅ Repositori berhasil di-pull:\n```\n{result.stdout}\n```\n\nSedang memulai ulang sistem (Restarting)...")
        
        # Restart the script
        os.execl(sys.executable, sys.executable, *sys.argv)
    except Exception as e:
        await status_msg.edit(f"❌ Gagal melakukan update: {e}")

@client.on(events.NewMessage(pattern='/panel'))
async def panel(event):
    if event.chat_id != ADMIN_ID:
        return
    await event.reply("🎛 **DramaBite Control Panel**", buttons=get_panel_buttons())

@client.on(events.CallbackQuery())
async def panel_callback(event):
    if event.sender_id != ADMIN_ID:
        return
    data = event.data
    try:
        if data == b"start_auto":
            BotState.is_auto_running = True
            await event.answer("Auto-mode started!")
            await event.edit("🎛 **DramaBite Control Panel**", buttons=get_panel_buttons())
        elif data == b"stop_auto":
            BotState.is_auto_running = False
            await event.answer("Auto-mode stopped!")
            await event.edit("🎛 **DramaBite Control Panel**", buttons=get_panel_buttons())
        elif data == b"status":
            await event.answer(f"Status: {'Running' if BotState.is_auto_running else 'Stopped'}")
            await event.edit("🎛 **DramaBite Control Panel**", buttons=get_panel_buttons())
    except Exception as e:
        if "message is not modified" in str(e).lower() or "Message string and reply markup" in str(e):
            pass
        else:
            logger.error(f"Callback error: {e}")

@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.reply("Welcome to DramaBite Downloader Bot! 🎉\n\nGunakan perintah `/download {bookId}` untuk mulai.")

@client.on(events.NewMessage(pattern=r'/download (\d+)'))
async def on_download(event):
    chat_id = event.chat_id
    if chat_id != ADMIN_ID:
        await event.reply("❌ Maaf, perintah ini hanya untuk admin.")
        return
    if BotState.is_processing:
        await event.reply("⚠️ Sedang memproses drama lain. Tunggu hingga selesai.")
        return
    book_id = event.pattern_match.group(1)
    
    # Check detail
    detail = await get_drama_detail(book_id)
    if not detail:
        await event.reply(f"❌ Gagal mendapatkan detail drama `{book_id}`.")
        return
        
    episodes = await get_all_episodes(book_id)
    if not episodes:
        await event.reply(f"❌ Drama `{book_id}` tidak memiliki episode.")
        return
        
    title = detail.get("title") or detail.get("name") or f"Drama_{book_id}"
    status_msg = await event.reply(f"🎬 Drama: **{title}**\n📽 Total Episodes: {len(episodes)}\n\n⏳ Sedang mendownload...")
    
    try:
        BotState.is_processing = True
        processed_ids.add(book_id)
        save_processed(processed_ids)
        
        await process_drama_full(book_id, chat_id, status_msg)
    finally:
        BotState.is_processing = False

async def process_drama_full(book_id, chat_id, status_msg=None):
    """DramaBite specific processing logic."""
    detail = await get_drama_detail(book_id)
    episodes = await get_all_episodes(book_id)
    
    if not detail or not episodes:
        if status_msg: await status_msg.edit(f"❌ Detail atau Episode `{book_id}` tidak ditemukan.")
        return False

    title = detail.get("title") or detail.get("name") or f"Drama_{book_id}"
    description = detail.get("desc") or detail.get("description") or "No description available."
    poster = detail.get("cover") or detail.get("poster") or ""
    
    temp_dir = tempfile.mkdtemp(prefix=f"dramabite_{book_id}_")
    video_dir = os.path.join(temp_dir, "episodes")
    os.makedirs(video_dir, exist_ok=True)
    
    try:
        if status_msg: await status_msg.edit(f"🎬 Processing **{title}**...")
        
        # Download (Now handles m3u8 in downloader.py)
        success = await download_all_episodes(episodes, video_dir)
        if not success:
            if status_msg: await status_msg.edit("❌ Download Gagal.")
            return False

        # Merge
        output_video_path = os.path.join(temp_dir, f"{title}.mp4")
        merge_success = merge_episodes(video_dir, output_video_path)
        if not merge_success:
            if status_msg: await status_msg.edit("❌ Merge Gagal.")
            return False

        # Upload
        upload_success = await upload_drama(
            client, chat_id, title, description, poster, output_video_path
        )
        
        if upload_success:
            if status_msg: await status_msg.delete()
            return True
        else:
            if status_msg: await status_msg.edit("❌ Upload Gagal.")
            return False
    except Exception as e:
        logger.error(f"Error processing {book_id}: {e}")
        if status_msg: await status_msg.edit(f"❌ Error: {e}")
        return False
    finally:
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception as e:
                logger.warning(f"Could not remove temp_dir {temp_dir}: {e}")

async def auto_mode_loop():
    """Loop to find and process new dramas from DramaBite."""
    global processed_ids
    logger.info("🚀 DramaBite Auto-Mode Started.")
    is_initial_run = True
    
    while True:
        if not BotState.is_auto_running:
            await asyncio.sleep(5)
            continue
            
        try:
            interval = 5 if is_initial_run else 15
            logger.info(f"🔍 Scanning sources (Next in {interval}m)...")
            
            # Source 1: Recommendation (Module)
            logger.info("🔍 Scanning module-recommendations...")
            rec_dramas = await get_latest_dramas(pages=2 if is_initial_run else 1) or []
            
            # Source 2: Home Page (Paling Populer, etc.)
            logger.info("🔍 Scanning home-list...")
            home_dramas = await get_home_dramas() or []
            
            # Filter and Combine
            new_queue = []
            seen_in_scan = set()
            
            for d in (rec_dramas + home_dramas):
                book_id = str(d.get("cid") or d.get("id") or "")
                if not book_id or book_id in seen_in_scan:
                    continue
                seen_in_scan.add(book_id)
                if book_id not in processed_ids:
                    new_queue.append(d)
            
            new_found = 0
            for drama in new_queue:
                if not BotState.is_auto_running: break
                    
                book_id = str(drama.get("cid") or drama.get("id"))
                title = drama.get("title") or "Unknown"
                
                processed_ids.add(book_id)
                save_processed(processed_ids)
                
                new_found += 1
                logger.info(f"✨ New discovery: {title} ({book_id}). Starting process...")
                
                try:
                    await client.send_message(ADMIN_ID, f"🆕 **Auto-System Mendeteksi Drama Baru!**\n🎬 `{title}`\n🆔 `{book_id}`\n⏳ Memproses...")
                except: pass
                
                try:
                    BotState.is_processing = True
                    success = await process_drama_full(book_id, AUTO_CHANNEL)
                    
                    if success:
                        logger.info(f"✅ Finished {title}")
                        try:
                            await client.send_message(ADMIN_ID, f"✅ Sukses Auto-Post: **{title}**")
                        except: pass
                    else:
                        logger.error(f"❌ Failed to process {title}")
                        try:
                            await client.send_message(ADMIN_ID, f"🚨 **ERROR**: Proses `{title}` gagal! Melewati ke judul berikutnya...")
                        except: pass
                except Exception as e:
                    logger.error(f"💥 Critical error in processing {title}: {e}")
                finally:
                    BotState.is_processing = False
                
                await asyncio.sleep(10) # Avoid flooding
            
            if new_found == 0:
                logger.info("😴 No new content.")
            
            is_initial_run = False
            for _ in range(interval * 60):
                if not BotState.is_auto_running: break
                await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"⚠️ Loop error: {e}")
            await asyncio.sleep(60)


if __name__ == '__main__':
    logger.info("Initializing Dramabox Auto-Bot...")
    
    # Start auto loop and keep the client running
    client.loop.create_task(auto_mode_loop())
    
    logger.info("Bot is active and monitoring.")
    client.run_until_disconnected()
