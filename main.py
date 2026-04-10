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
from firebase_utils import is_title_uploaded, mark_title_as_uploaded

# Configuration
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
AUTO_CHANNEL = int(os.environ.get("AUTO_CHANNEL", ADMIN_ID))
TOPIC_ID = int(os.environ.get("TOPIC_ID", "0"))
PROCESSED_FILE = "processed.json"

def sanitize_filename(filename):
    """Remove invalid characters from filenames."""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '')
    return filename.strip()

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
        # Always upload to AUTO_CHANNEL / TOPIC_ID as requested
        await process_drama_full(book_id, chat_id, status_msg, target_chat=AUTO_CHANNEL, target_topic=TOPIC_ID)
    finally:
        BotState.is_processing = False

async def download_progress_callback(current, total, event, title, start_time):
    """Update progress for downloading phase."""
    # Bar
    bar_length = 10
    filled_length = int(bar_length * current // total)
    bar = '■' * filled_length + '□' * (bar_length - filled_length)
    
    # ETC
    import time
    elapsed_time = time.time() - start_time
    if current > 0:
        total_time = (elapsed_time / current) * total
        remaining_time = total_time - elapsed_time
        mins, secs = divmod(int(remaining_time), 60)
        etc = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"
    else:
        etc = "Calculating..."

    status_text = (
        f"🎬 **{title}**\n"
        f"🔥 **Status:** download...\n"
        f"🎞 **Episode** {current}/{total}\n"
        f"|{bar}| {int(current/total*100)}%\n"
        f"⏳ **Estimasi Selesai:** {etc}"
    )
    
    try:
        await event.edit(status_text)
    except:
        pass

async def process_drama_full(book_id, chat_id, status_msg=None, target_chat=None, target_topic=None):
    """DramaBite specific processing logic."""
    # Fallback to chat_id if target not specified
    target_chat = target_chat or chat_id
    
    detail = await get_drama_detail(book_id)
    episodes = await get_all_episodes(book_id)
    
    if not detail:
        error_msg = f"❌ Detail drama `{book_id}` tidak ditemukan di API."
        if status_msg: await status_msg.edit(error_msg)
        await client.send_message(ADMIN_ID, f"🚨 **PROSES GAGAL**: `{book_id}`\nAlasan: Detail drama tidak ditemukan.")
        return False
        
    if not episodes:
        error_msg = f"❌ Episode untuk drama `{book_id}` tidak ditemukan di API."
        if status_msg: await status_msg.edit(error_msg)
        await client.send_message(ADMIN_ID, f"🚨 **PROSES GAGAL**: `{book_id}`\nAlasan: Drama tidak memiliki episode.")
        return False

    title = detail.get("title") or detail.get("name") or f"Drama_{book_id}"
    description = detail.get("desc") or detail.get("description") or "No description available."
    poster = detail.get("cover") or detail.get("poster") or ""
    
    # Gunakan folder temp lokal untuk menghindari masalah FFmpeg Snap Confinement
    base_temp = os.path.join(os.getcwd(), "temp")
    os.makedirs(base_temp, exist_ok=True)
    
    temp_dir = tempfile.mkdtemp(prefix=f"dramabite_{book_id}_", dir=base_temp)
    video_dir = os.path.join(temp_dir, "episodes")
    os.makedirs(video_dir, exist_ok=True)
    
    try:
        if status_msg: await status_msg.edit(f"🎬 Processing **{title}**...")
        
        # --- FIREBASE CHECK ---
        if is_title_uploaded(title):
            if status_msg: await status_msg.edit(f"⏭ **{title}** sudah pernah di-upload. Skip.")
            logger.info(f"Skip {title} - sudah ada di Firebase.")
            return True # Anggap sukses agar loop lanjut k id berikutnya
        # ----------------------
        
        # Download
        import time
        download_start_time = time.time()

        async def p_callback(c, t):
            if status_msg:
                await download_progress_callback(c, t, status_msg, title, download_start_time)

        success_count, total_count = await download_all_episodes(
            episodes, video_dir, progress_callback=p_callback
        )
        
        if success_count == 0:
            err_text = f"❌ Download Gagal: 0/{total_count} episode berhasil."
            if status_msg: await status_msg.edit(err_text)
            try:
                await client.send_message(ADMIN_ID, f"🚨 **PROSES GAGAL**: `{title}`\nAlasan: Gagal mendownload episode (FFmpeg Error).")
            except: pass
            return False
            
        if success_count < total_count:
            logger.warning(f"⚠️ Only {success_count}/{total_count} episodes downloaded for {title}. Proceeding with partial content.")
            if status_msg: await status_msg.edit(f"🎬 Processing **{title}** ({success_count}/{total_count} eps)...")

        # Merge
        safe_title = sanitize_filename(title)
        output_video_path = os.path.join(temp_dir, f"{safe_title}.mp4")
        merge_success = merge_episodes(video_dir, output_video_path)
        if not merge_success:
            err_text = f"❌ Merge Gagal (Total {success_count} eps)."
            if status_msg: await status_msg.edit(err_text)
            try:
                await client.send_message(ADMIN_ID, f"🚨 **PROSES GAGAL**: `{title}`\nAlasan: Gagal saat proses merging (FFmpeg Merge Error).")
            except: pass
            return False

        # Upload
        upload_success = await upload_drama(
            client, target_chat, title, description, poster, output_video_path, 
            topic_id=target_topic, episodes_count=len(episodes)
        )
        
        if upload_success:
            # --- FIREBASE SAVE ---
            mark_title_as_uploaded(title)
            # ---------------------
            if status_msg: await status_msg.delete()
            return True
        else:
            if status_msg: await status_msg.edit("❌ Upload Gagal.")
            try:
                await client.send_message(ADMIN_ID, f"🚨 **PROSES GAGAL**: `{title}`\nAlasan: Gagal saat mengunggah ke Telegram.")
            except: pass
            return False
    except Exception as e:
        logger.error(f"Error processing {book_id}: {e}")
        if status_msg: await status_msg.edit(f"❌ Error: {e}")
        try:
            await client.send_message(ADMIN_ID, f"💥 **CRITICAL ERROR**: `{title}`\nAlasan: {str(e)[:200]}")
        except: pass
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
            rec_dramas = await get_latest_dramas(pages=3 if is_initial_run else 2) or []
            
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
                
                new_found += 1
                logger.info(f"✨ New discovery: {title} ({book_id}). Starting process...")
                
                try:
                    await client.send_message(ADMIN_ID, f"🆕 **Auto-System Mendeteksi Drama Baru!**\n🎬 `{title}`\n🆔 `{book_id}`\n⏳ Memproses...")
                except: pass
                
                try:
                    BotState.is_processing = True
                    success = await process_drama_full(book_id, AUTO_CHANNEL, target_topic=TOPIC_ID)
                    
                    if success:
                        processed_ids.add(book_id)
                        save_processed(processed_ids)
                        logger.info(f"✅ Finished {title}")
                        try:
                            await client.send_message(ADMIN_ID, f"✅ Sukses Auto-Post: **{title}**")
                        except: pass
                    else:
                        logger.error(f"❌ Failed to process {title}")
                        try:
                            # We still mark it as processed even if it fails to avoid infinite loops of failure
                            # but we do it after the attempt.
                            processed_ids.add(book_id)
                            save_processed(processed_ids)
                            # Pesan spesifik sudah dikirim oleh process_drama_full
                            pass
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
    logger.info("Initializing DramaBite Auto-Bot...")
    
    # Bersihkan folder temp lama saat startup agar tidak menumpuk
    base_temp = os.path.join(os.getcwd(), "temp")
    if os.path.exists(base_temp):
        logger.info("🧹 Membersihkan folder temp lama...")
        shutil.rmtree(base_temp, ignore_errors=True)
    os.makedirs(base_temp, exist_ok=True)
    
    # Start auto loop and keep the client running
    client.loop.create_task(auto_mode_loop())
    
    logger.info("Bot is active and monitoring.")
    client.run_until_disconnected()
