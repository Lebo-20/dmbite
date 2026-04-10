import os
import asyncio
from telethon import TelegramClient, events
from telethon.tl.types import DocumentAttributeVideo
import logging

logger = logging.getLogger(__name__)

import time

async def upload_progress(current, total, event, title, start_time, episodes_count=None):
    """Callback function for upload progress with Bar and ETC."""
    if total == 0: return
    
    percentage = (current / total) * 100
    
    # Avoid flood by updating every 5%
    last_percent = getattr(event, '_last_percent', -5)
    if int(percentage) - last_percent < 5 and current < total:
        return
    event._last_percent = int(percentage)

    # Bar
    bar_length = 10
    filled_length = int(bar_length * current // total)
    bar = '■' * filled_length + '□' * (bar_length - filled_length)
    
    # ETC
    elapsed_time = time.time() - start_time
    if current > 0:
        total_time = (elapsed_time / current) * total
        remaining_time = total_time - elapsed_time
        mins, secs = divmod(int(remaining_time), 60)
        etc = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"
    else:
        etc = "Calculating..."

    ep_info = f"🎞 **Episode:** {episodes_count}/{episodes_count}\n" if episodes_count else ""
    
    status_text = (
        f"🎬 **{title}**\n"
        f"🔥 **Status:** upload...\n"
        f"{ep_info}"
        f"|{bar}| {percentage:.0f}%\n"
        f"⏳ **Estimasi Selesai:** {etc}"
    )
    
    try:
        await event.edit(status_text)
    except:
        pass

async def upload_drama(client: TelegramClient, chat_id: int, 
                       title: str, description: str, 
                       poster_url: str, video_path: str,
                       topic_id: int = None, episodes_count: int = None):
    """
    Uploads the drama information and merged video to Telegram.
    """
    import subprocess
    import tempfile
    try:
        # Resolve entity if ID is a number (especially for private groups/channels)
        try:
            entity = await client.get_entity(chat_id)
            target = entity
        except Exception as e:
            logger.warning(f"Entity mismatch for {chat_id}, refreshing dialogs...")
            # Ambil semua percakapan bot untuk update cache ID
            await client.get_dialogs()
            try:
                entity = await client.get_entity(chat_id)
                target = entity
            except:
                logger.error(f"STILL could not resolve entity for {chat_id}")
                target = chat_id
            
        # 1. Send Poster + Description as PHOTO (not file)
        caption = f"🎬 **{title}**\n\n📝 **Sinopsis:**\n{description[:500]}..."
        
        # Download poster to temp file first so Telethon sends it as photo
        import httpx
        poster_path = None
        try:
            async with httpx.AsyncClient(timeout=30) as http_client:
                resp = await http_client.get(poster_url)
                if resp.status_code == 200:
                    poster_path = os.path.join(tempfile.gettempdir(), f"poster_{title[:20].replace(' ','_')}.jpg")
                    with open(poster_path, "wb") as pf:
                        pf.write(resp.content)
        except Exception as e:
            logger.warning(f"Failed to download poster: {e}")
        
        # Send caption (with optional poster)
        poster_to_send = poster_path or poster_url
        try:
            if poster_to_send:
                await client.send_message(target, caption, file=poster_to_send, parse_mode='md', reply_to=topic_id)
            else:
                await client.send_message(target, caption, parse_mode='md', reply_to=topic_id)
        except Exception as e:
            logger.error(f"Failed to send poster: {e}")
            await client.send_message(target, caption, parse_mode='md', reply_to=topic_id)
        
        # Cleanup poster temp file
        if poster_path and os.path.exists(poster_path):
            os.remove(poster_path)
        
        status_msg = await client.send_message(target, "📤 Ekstraksi Thumbnail & Durasi Video...", reply_to=topic_id)
        
        # 2. Extract Duration & Dimensions (Fallback directly if fails)
        duration = 0
        width = 0
        height = 0
        try:
            ffprobe_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=width,height", "-of", "default=noprint_wrappers=1:nokey=1", video_path]
            output = subprocess.check_output(ffprobe_cmd, text=True).strip().split('\n')
            if len(output) >= 3:
                width = int(output[0])
                height = int(output[1])
                duration = int(float(output[2]))
        except Exception as e:
            logger.warning(f"Failed to extract video info: {e}")

        # 3. Extract Thumbnail
        thumb_path = os.path.join(tempfile.gettempdir(), f"thumb_{os.path.basename(video_path)}.jpg")
        try:
            subprocess.run(["ffmpeg", "-y", "-i", video_path, "-ss", "00:00:01.000", "-vframes", "1", thumb_path], capture_output=True)
            if not os.path.exists(thumb_path):
                thumb_path = None
        except Exception as e:
            logger.warning(f"Failed to generate thumbnail: {e}")
            thumb_path = None

        await status_msg.edit("📤 Sedang mengupload video ke Telegram...")
        
        from telethon.tl.types import DocumentAttributeVideo
        video_attributes = [
            DocumentAttributeVideo(
                duration=duration,
                w=width,
                h=height,
                supports_streaming=True
            )
        ]
        
        start_time = time.time()
        await client.send_file(
            target,
            video_path,
            caption=f"🎥 Full Episode: {title}",
            force_document=False, # FORCE IT AS VIDEO STREAM
            thumb=thumb_path,
            attributes=video_attributes,
            progress_callback=lambda c, t: upload_progress(c, t, status_msg, title, start_time, episodes_count),
            supports_streaming=True,
            reply_to=topic_id
        )
        
        await status_msg.delete()
        if thumb_path and os.path.exists(thumb_path):
            os.remove(thumb_path)
            
        logger.info(f"Successfully uploaded {title} to Telegram")
        return True
    except Exception as e:
        logger.error(f"Failed to upload to Telegram: {e}")
        return False
