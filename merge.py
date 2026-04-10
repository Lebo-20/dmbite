import os
import subprocess
import logging

logger = logging.getLogger(__name__)

def merge_episodes(video_dir: str, output_path: str):
    """
    Merges all .mp4 files in video_dir into a single output_path file.
    Returns: List of file paths to upload (can be multiple parts if split).
    """
    try:
        # Get all video files
        files = [f for f in os.listdir(video_dir) if f.endswith(".mp4")]
        if not files:
            logger.error(f"No .mp4 files found in {video_dir} to merge.")
            return []
            
        files.sort()
        logger.info(f"Found {len(files)} files to merge in {video_dir}")
        
        list_file_path = os.path.join(video_dir, "list.txt")
        # Gunakan path absolut agar FFmpeg tidak bingung
        with open(list_file_path, "w", encoding='utf-8') as f:
            for file in files:
                abs_path = os.path.abspath(os.path.join(video_dir, file))
                # Di Windows, path harus menggunakan forward slash untuk concat list FFmpeg
                abs_path = abs_path.replace("\\", "/")
                f.write(f"file '{abs_path}'\n")

        # 1. First attempt: -c copy (Sangat Cepat)
        command = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", list_file_path,
            "-c", "copy",
            output_path
        ]
        
        logger.info("Mencoba Merge Cepat (-c copy)...")
        process = subprocess.run(command, capture_output=True, text=True)
        
        if process.returncode == 0:
            logger.info(f"✅ Berhasil Merge Cepat: {output_path}")
            return check_and_prepare_files(output_path)
        else:
            logger.error(f"❌ MERGE GAGAL: Video tidak bisa digabung secara langsung.\nError: {process.stderr}")
            return []
            
    except Exception as e:
        logger.error(f"💥 Error fatal saat merge: {e}")
        return False

# Hapus kompresi, ganti dengan Split tanpa re-encode
def check_and_prepare_files(video_path: str):
    """
    Cek jika file lebih dari 1.9 GB, jika ya, split menjadi beberapa bagian tanpa re-encode.
    Menggunakan mode segment agar cepat dan kualitas tetap asli.
    Returns: List of file paths to upload.
    """
    try:
        size_bytes = os.path.getsize(video_path)
        limit_bytes = 1900 * 1024 * 1024 # 1.9 GB
        
        if size_bytes <= limit_bytes:
            return [video_path]
            
        logger.warning(f"⚠️ File terlalu besar ({size_bytes / (1024**3):.2f} GB). Memecah menjadi beberapa bagian (Tanpa Re-encode)...")
        
        # Nama dasar: "Judul Drama.mp4" -> "Judul Drama - Part %d.mp4"
        output_pattern = video_path.replace(".mp4", " - Part %01d.mp4")
        
        # Hitung estimasi waktu split per 1.9GB 
        # (Kita gunakan duration-based split atau size-based)
        # Cara termudah tanpa re-encode adalah menggunakan -f segment
        command = [
            "ffmpeg", "-y", "-i", video_path,
            "-c", "copy", "-map", "0",
            "-f", "segment", "-segment_time", "3600", # Split per 1 jam (estimasi aman untuk < 2GB)
            "-reset_timestamps", "1",
            output_pattern
        ]
        
        process = subprocess.run(command, capture_output=True, text=True)
        if process.returncode == 0:
            # Cari file hasil part
            base_dir = os.path.dirname(video_path)
            base_name = os.path.basename(video_path).replace(".mp4", " - Part")
            parts = [os.path.join(base_dir, f) for f in os.listdir(base_dir) if f.startswith(base_name)]
            parts.sort()
            
            if parts:
                os.remove(video_path) # Hapus file raksasa asli
                logger.info(f"✅ Berhasil memecah menjadi {len(parts)} bagian.")
                return parts
        
        return [video_path] # Balikkan asli jika gagal
    except Exception as e:
        logger.error(f"Error during splitting: {e}")
        return [video_path]
