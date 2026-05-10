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
                       topic_id: int = None, episodes_count: int = None,
                       skip_metadata: bool = False, part_number: int = None):
    """
    Uploads the drama information and merged video to Telegram.
    skip_metadata: If True, only uploads the video without poster/synopsis.
    """
    import subprocess
    import tempfile
    
    # Normalize topic_id
    if not topic_id or topic_id == 0:
        topic_id = None
    else:
        try:
            topic_id = int(topic_id)
        except:
            topic_id = None

    try:
        # 1. Send Poster + Description (Only if not skipping)
        if not skip_metadata:
            # Format Caption yang lebih lengkap
            ep_info = f"\n📂 **Total Episode:** {episodes_count}" if episodes_count else ""
            clean_desc = description.strip() if description and description.strip() != "-" else "Tidak ada sinopsis."
            caption = f"🎬 **{title}**{ep_info}\n\n📝 **Sinopsis:**\n{clean_desc[:800]}..."
            
            import httpx
            poster_path = None
            try:
                if poster_url and poster_url.startswith("http"):
                    logger.info(f"Downloading poster from {poster_url}...")
                    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as http_client:
                        resp = await http_client.get(poster_url)
                        if resp.status_code == 200:
                            poster_path = os.path.join(tempfile.gettempdir(), f"poster_{int(time.time())}.jpg")
                            with open(poster_path, "wb") as pf:
                                pf.write(resp.content)
                else:
                    logger.warning("Poster URL is invalid or empty.")
            except Exception as e:
                logger.warning(f"Failed to download poster: {e}")
            
            poster_to_send = poster_path or None
            try:
                if poster_to_send:
                    await client.send_message(chat_id, caption, file=poster_to_send, parse_mode='md', reply_to=topic_id)
                else:
                    # Kirim teks saja jika poster gagal total
                    await client.send_message(chat_id, caption, parse_mode='md', reply_to=topic_id)
            except Exception as e:
                logger.error(f"Failed to send poster: {e}")
                await client.send_message(chat_id, caption, parse_mode='md', reply_to=topic_id)
            
            if poster_path and os.path.exists(poster_path):
                os.remove(poster_path)
        
        # 2. Prepare Video Upload
        part_info = f" (Part {part_number})" if part_number else ""
        status_msg = await client.send_message(chat_id, f"📤 Menyiapkan video{part_info}...", reply_to=topic_id)
        
        # Metadata extraction
        duration, width, height = 0, 0, 0
        try:
            ffprobe_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=width,height", "-of", "default=noprint_wrappers=1:nokey=1", video_path]
            output = subprocess.check_output(ffprobe_cmd, text=True).strip().split('\n')
            if len(output) >= 3:
                try:
                    width = int(output[0])
                    height = int(output[1])
                    duration = int(float(output[2]))
                except: pass
        except Exception as e:
            logger.warning(f"Metadata extraction failed: {e}")

        # Thumbnail extraction
        thumb_path = os.path.join(tempfile.gettempdir(), f"thumb_{int(time.time())}.jpg")
        try:
            subprocess.run(["ffmpeg", "-y", "-i", video_path, "-ss", "00:00:02.000", "-vframes", "1", thumb_path], capture_output=True)
            if not os.path.exists(thumb_path):
                thumb_path = None
        except:
            thumb_path = None

        # 3. Upload with Retries
        max_retries = 3
        upload_success = False
        last_error = ""
        
        # Display part info in progress
        display_title = f"{title}{part_info}" if part_number else title

        for attempt in range(1, max_retries + 1):
            try:
                await status_msg.edit(f"📤 Uploading {display_title}... (Attempt {attempt}/{max_retries})")
                
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
                    chat_id,
                    video_path,
                    caption=f"🎥 **{display_title}**",
                    force_document=False,
                    thumb=thumb_path,
                    attributes=video_attributes,
                    progress_callback=lambda c, t: upload_progress(c, t, status_msg, display_title, start_time, episodes_count),
                    supports_streaming=True,
                    reply_to=topic_id
                )
                upload_success = True
                break
            except Exception as e:
                last_error = str(e)
                logger.error(f"Upload attempt {attempt} failed for {display_title}: {e}")
                if attempt < max_retries:
                    await asyncio.sleep(5)
        
        await status_msg.delete()
        if thumb_path and os.path.exists(thumb_path):
            os.remove(thumb_path)
            
        if upload_success:
            logger.info(f"Successfully uploaded {display_title}")
            return True
        else:
            logger.error(f"All upload attempts failed for {display_title}. Last error: {last_error}")
            return False
            
    except Exception as e:
        logger.error(f"Critical error in upload_drama: {e}")
        return False


