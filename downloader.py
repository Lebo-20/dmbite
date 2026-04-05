import os
import asyncio
import logging
import subprocess

logger = logging.getLogger(__name__)

async def download_m3u8(url: str, path: str, retries: int = 3):
    """Downloads an m3u8 playlist using ffmpeg and converts it to mp4, with retries."""
    for attempt in range(1, retries + 1):
        try:
            # -y (overwrite), -i (input), -c copy (fast as it doesn't re-encode)
            # Added User-Agent as many scrapers require it
            cmd = [
                "ffmpeg", "-y", 
                "-user_agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                "-i", url,
                "-c", "copy", "-bsf:a", "aac_adtstoasc",
                "-loglevel", "error",
                path
            ]
            
            logger.info(f"💾 Downloading m3u8: {path} via FFmpeg (Attempt {attempt}/{retries})")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                # 10 minutes timeout per episode
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=600)
            except asyncio.TimeoutError:
                try:
                    process.terminate()
                except:
                    pass
                logger.error(f"FFmpeg download timed out for {url}")
                continue
                
            if process.returncode == 0:
                return True
            else:
                err = stderr.decode()
                logger.error(f"FFmpeg failed with exit code {process.returncode} for {url}. Error: {err}")
                if "403 Forbidden" in err or "404 Not Found" in err:
                    # No point in retrying if it's a 4xx error usually, but we'll try anyway if requested
                    pass
                
        except Exception as e:
            logger.error(f"FFmpeg exception for {url} on attempt {attempt}: {e}")
            
        if attempt < retries:
            await asyncio.sleep(2) # Wait before retry
            
    return False

async def download_all_episodes(episodes, download_dir: str, semaphore_count: int = 5):
    """
    Downloads all episodes concurrently using FFmpeg for m3u8 support.
    Returns (success_count, total_count).
    """
    os.makedirs(download_dir, exist_ok=True)
    semaphore = asyncio.Semaphore(semaphore_count)
    total_count = len(episodes)

    async def limited_download(ep):
        async with semaphore:
            # Sort episodes by vid or episode number
            vid = ep.get('vid') or ep.get('episode') or 'unk'
            try:
                ep_num = str(vid).zfill(3)
            except:
                ep_num = str(vid)
                
            filename = f"episode_{ep_num}.mp4"
            filepath = os.path.join(download_dir, filename)
            
            # Use 'url' for DramaBite, or fallback to 'playUrl' / 'videos'
            url = ep.get('url') or ep.get('playUrl')
            if not url and 'videos' in ep:
                videos = ep.get('videos', [])
                if isinstance(videos, list) and videos:
                    url = videos[0].get('url')
            
            if not url:
                logger.error(f"No URL found for episode {ep_num}")
                return False
                
            logger.info(f"Downloading episode {ep_num} from {url}...")
            
            # All DramaBite links are m3u8, use ffmpeg
            if ".m3u8" in url.lower() or "m3u8" in url:
                success = await download_m3u8(url, filepath)
            else:
                # Fallback for direct MP4 if any exists
                import httpx
                async with httpx.AsyncClient(timeout=60) as client:
                    success = await download_file_inner(client, url, filepath)
            
            if success:
                logger.info(f"✅ Downloaded {filename}")
            else:
                logger.error(f"❌ Failed to download {filename} after all attempts.")
            return success

    results = await asyncio.gather(*(limited_download(ep) for ep in episodes))
    success_count = sum(1 for r in results if r)
    return success_count, total_count

async def download_file_inner(client, url, path, retries: int = 2):
    """Fallback binary downloader for non-m3u8 files with retries."""
    for attempt in range(1, retries + 1):
        try:
            async with client.stream("GET", url, timeout=60) as response:
                response.raise_for_status()
                with open(path, "wb") as f:
                    async for chunk in response.aiter_bytes():
                        f.write(chunk)
            return True
        except Exception as e:
            logger.error(f"Binary download failed for {url} (Attempt {attempt}/{retries}): {e}")
            if attempt < retries:
                await asyncio.sleep(2)
    return False
