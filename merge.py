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
    Cek jika file lebih dari 1.99 GB, jika ya, split menjadi beberapa bagian tanpa re-encode.
    Menggunakan mode segment agar cepat dan kualitas tetap asli.
    Returns: List of file paths to upload.
    """
    try:
        size_bytes = os.path.getsize(video_path)
        # 1.99 GB = 1.99 * 1024 * 1024 * 1024 bytes
        limit_bytes = int(1.99 * 1024 * 1024 * 1024) 
        
        if size_bytes <= limit_bytes:
            return [video_path]
            
        logger.warning(f"⚠️ File terlalu besar ({size_bytes / (1024**3):.2f} GB). Memecah menjadi bagian-bagian 1.99GB (Tanpa Re-encode)...")
        
        # Nama dasar untuk part: "Drama.mp4" -> "Drama - Part %d.mp4"
        # Kita gunakan format yang konsisten untuk dideteksi nanti
        output_pattern = video_path.replace(".mp4", " - Part %01d.mp4")
        
        # Gunakan segment_size untuk memecah berdasarkan ukuran
        # Note: ffmpeg akan memecah pada keyframe terdekat SETELAH ukuran tercapai
        command = [
            "ffmpeg", "-y", "-i", video_path,
            "-c", "copy", "-map", "0",
            "-f", "segment", 
            "-segment_size", "1990M", # 1.99 GB per part
            "-reset_timestamps", "1",
            "-initial_offset", "0",
            output_pattern
        ]
        
        process = subprocess.run(command, capture_output=True, text=True)
        if process.returncode == 0:
            # Cari file hasil part
            base_dir = os.path.dirname(video_path)
            # Ambil nama file tanpa ekstensi untuk mencocokkan pattern
            name_no_ext = os.path.basename(video_path).replace(".mp4", "")
            base_name_pattern = f"{name_no_ext} - Part"
            
            parts = [os.path.join(base_dir, f) for f in os.listdir(base_dir) if f.startswith(base_name_pattern)]
            parts.sort()
            
            if parts:
                os.remove(video_path) # Hapus file raksasa asli
                logger.info(f"✅ Berhasil memecah menjadi {len(parts)} bagian berdasarkan ukuran.")
                return parts
        
        logger.error(f"Gagal memecah file: {process.stderr}")
        return [video_path] # Balikkan asli jika gagal
    except Exception as e:
        logger.error(f"Error during splitting: {e}")
        return [video_path]
