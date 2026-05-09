import os
import asyncio
import logging
import shutil
import tempfile
import random
import time
import sys
from telethon import TelegramClient, events, Button
from telethon.tl.types import DocumentAttributeVideo
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
TOPIC_ID = os.environ.get("TOPIC_ID", "0")

# Normalize TOPIC_ID
if not TOPIC_ID or TOPIC_ID == "0" or TOPIC_ID == "":
    TOPIC_ID = None
else:
    try:
        TOPIC_ID = int(TOPIC_ID)
    except:
        TOPIC_ID = None

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize client
client = TelegramClient('dramabite_bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# Bot State
class BotState:
    is_processing = False
    task_queue = asyncio.Queue()
    current_task = None
    processed_titles = set()

class UserState:
    waiting_for_id = {} # sender_id: bool

# --- WORKER SYSTEM ---

async def worker():
    """Worker to process tasks from queue sequentially."""
    logger.info("👷 Worker system started.")
    while True:
        book_id, admin_id, is_manual = await BotState.task_queue.get()
        BotState.is_processing = True
        
        try:
            await process_drama_full(book_id, admin_id, target_chat=AUTO_CHANNEL, target_topic=TOPIC_ID, is_manual=is_manual)
        except Exception as e:
            logger.error(f"Worker error on {book_id}: {e}")
        finally:
            BotState.is_processing = False
            BotState.current_task = None
            BotState.task_queue.task_done()

# --- CORE LOGIC ---

async def process_drama_full(book_id, admin_id, target_chat=None, target_topic=None, is_manual=False):
    tag = "📥 [MANUAL]" if is_manual else "🤖 [AUTO]"
    status_msg = None
    
    try:
        # 1. Fetch Detail
        drama = await get_drama_detail(book_id)
        if not drama:
            await client.send_message(admin_id, f"{tag} Gagal mendapatkan detail drama ID `{book_id}`.")
            return False
            
        title = drama.get('title') or drama.get('name') or f"Drama_{book_id}"
        description = drama.get('description') or "-"
        poster = drama.get('horizontal_poster') or drama.get('vertical_poster')
        
        BotState.current_task = title

        # Check Firebase
        if is_title_uploaded(title):
            logger.info(f"Skip {title} - already uploaded.")
            if is_manual:
                await client.send_message(admin_id, f"{tag} **{title}** sudah pernah di-upload. Skip.")
            return True

        episodes = await get_all_episodes(book_id)
        if not episodes:
            await client.send_message(admin_id, f"{tag} **{title}** tidak memiliki episode.")
            return False

        status_msg = await client.send_message(admin_id, f"{tag} Memulai proses **{title}** ({len(episodes)} eps)...")

        # 2. Preparation & Download
        base_temp = os.path.join(os.getcwd(), "temp")
        if os.path.exists(base_temp):
            shutil.rmtree(base_temp, ignore_errors=True)
        os.makedirs(base_temp, exist_ok=True)
        
        temp_dir = tempfile.mkdtemp(prefix=f"dramabite_{book_id}_", dir=base_temp)
        video_dir = os.path.join(temp_dir, "episodes")
        os.makedirs(video_dir, exist_ok=True)

        await status_msg.edit(f"{tag} **{title}**\n📍 Tahap: **Download Episodes**...")
        success_count, total_count = await download_all_episodes(episodes, video_dir)
        
        if success_count < total_count:
            await client.send_message(admin_id, f"❌ {tag} **{title}** GAGAL pada tahap **DOWNLOAD**.\nBerhasil: {success_count}/{total_count}")
            return False

        # 3. Merging
        await status_msg.edit(f"{tag} **{title}**\n📍 Tahap: **Merging (-c copy)**...")
        from merge import merge_episodes, check_and_prepare_files
        merged_video_path = os.path.join(temp_dir, f"{title}.mp4")
        # merge_episodes returns the combined path
        result_path = await merge_episodes(video_dir, title)
        
        if not result_path or not os.path.exists(result_path):
            await client.send_message(admin_id, f"❌ {tag} **{title}** GAGAL pada tahap **MERGING**.")
            return False

        # 4. Splitting (Size-based 1.99GB)
        merged_files = check_and_prepare_files(result_path)

        # 5. Uploading
        await status_msg.edit(f"{tag} **{title}**\n📍 Tahap: **Uploading to Telegram**...")
        overall_success = True
        for i, file_path in enumerate(merged_files):
            is_first_part = (i == 0)
            part_num = (i + 1) if len(merged_files) > 1 else None
            
            upload_success = await upload_drama(
                client, target_chat, title, description, poster, file_path, 
                topic_id=target_topic, episodes_count=len(episodes),
                skip_metadata=not is_first_part,
                part_number=part_num
            )
            if not upload_success:
                overall_success = False
                break
        
        if overall_success:
            mark_title_as_uploaded(title)
            await status_msg.edit(f"✅ {tag} **{title}** BERHASIL di-upload!")
            return True
        else:
            await client.send_message(admin_id, f"❌ {tag} **{title}** GAGAL pada tahap **UPLOADING**.")
            return False

    except Exception as e:
        logger.error(f"Process Error: {e}")
        if status_msg: await status_msg.edit(f"❌ {tag} Terjadi kesalahan: {e}")
        return False
    finally:
        # Cleanup is handled by finally in worker or per drama?
        # We do it here to ensure temp is cleared.
        if 'temp_dir' in locals() and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

# --- UI & HANDLERS ---

async def get_main_menu():
    return [
        [Button.inline("📊 Cek Status", b"status"), Button.inline("📥 Download Manual", b"manual_dl")],
        [Button.inline("🔄 Update GitHub", b"update_git")],
        [Button.inline("⏹ Stop Auto-Mode", b"stop_auto"), Button.inline("▶️ Start Auto-Mode", b"start_auto")]
    ]

@client.on(events.NewMessage(pattern='/dramabite_help'))
@client.on(events.NewMessage(pattern='/start'))
async def help_handler(event):
    if event.sender_id != ADMIN_ID: return
    text = (
        "👋 **DramaBite Bot Control Panel**\n\n"
        "Gunakan tombol di bawah untuk mengoperasikan bot:"
    )
    await event.reply(text, buttons=await get_main_menu())

@client.on(events.CallbackQuery())
async def callback_handler(event):
    if event.sender_id != ADMIN_ID: return
    data = event.data
    
    if data == b"status":
        status = "🔴 Sibuk" if BotState.is_processing else "🟢 Standby"
        q_size = BotState.task_queue.qsize()
        msg = f"📊 **Status Bot**\n\nStatus: {status}\nAntrean: {q_size} tugas"
        if BotState.current_task:
            msg += f"\nSedang memproses: `{BotState.current_task}`"
        await event.answer(msg, alert=True)
        
    elif data == b"manual_dl":
        UserState.waiting_for_id[event.sender_id] = True
        await event.respond("🆔 **Silakan masukkan ID Drama:**\n(Kirim ID-nya saja, contoh: `10960`)", buttons=Button.inline("Batal", b"cancel_dl"))
        await event.answer()

    elif data == b"cancel_dl":
        UserState.waiting_for_id[event.sender_id] = False
        await event.edit("❌ Download manual dibatalkan.", buttons=await get_main_menu())
        await event.answer()

    elif data == b"update_git":
        await event.answer("🔄 Memproses update...")
        await run_update(event)

async def run_update(event):
    import subprocess
    msg = await event.respond("🔄 **GitHub**: Menghubungi repositori `Lebo-20/dmbite`...")
    try:
        # Jalankan git pull origin main secara eksplisit
        res = subprocess.run(["git", "pull", "origin", "main"], capture_output=True, text=True)
        
        if "Already up to date" in res.stdout:
            await msg.edit("✅ **GitHub**: Kode sudah versi terbaru.")
        elif res.returncode == 0:
            await msg.edit(f"✅ **GitHub Update Berhasil!**\n\n```\n{res.stdout[:500]}\n```\n\n*Bot perlu di-restart (PM2 restart) untuk menerapkan.*")
        else:
            await msg.edit(f"❌ **GitHub Update Gagal!**\n\nError: `{res.stderr}`")
    except Exception as e:
        await msg.edit(f"❌ **GitHub Error**: {e}")

@client.on(events.NewMessage())
async def message_handler(event):
    if event.sender_id != ADMIN_ID: return
    if UserState.waiting_for_id.get(event.sender_id):
        book_id = event.text.strip()
        if book_id.isdigit() or len(book_id) > 10:
            UserState.waiting_for_id[event.sender_id] = False
            await event.reply(f"✅ ID `{book_id}` masuk antrean prioritas.")
            await BotState.task_queue.put((book_id, ADMIN_ID, True))
        else:
            await event.reply("❌ ID tidak valid. Masukkan angka ID saja.")

# --- AUTO SCAN ---

async def auto_scan_loop():
    while True:
        logger.info("🔍 Auto-Scanning for new dramas...")
        try:
            recs = await get_latest_dramas(pages=2)
            home = await get_home_dramas()
            
            seen = set()
            for d in (recs + home):
                bid = str(d.get('id') or d.get('cid'))
                if bid not in seen:
                    await BotState.task_queue.put((bid, ADMIN_ID, False))
                    seen.add(bid)
        except Exception as e:
            logger.error(f"Auto-Scan Error: {e}")
        
        await asyncio.sleep(1800) # 30 mins

if __name__ == '__main__':
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    # Start systems
    client.loop.create_task(worker())
    client.loop.create_task(auto_scan_loop())
    
    logger.info("🚀 DramaBite Bot is online!")
    client.run_until_disconnected()
