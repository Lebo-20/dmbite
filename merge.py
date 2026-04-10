import os
import subprocess
import logging

logger = logging.getLogger(__name__)

def merge_episodes(video_dir: str, output_path: str):
    """
    Merges all .mp4 files in video_dir into a single output_path file.
    """
    try:
        # Get all video files
        files = [f for f in os.listdir(video_dir) if f.endswith(".mp4")]
        if not files:
            logger.error(f"No .mp4 files found in {video_dir} to merge.")
            return False
            
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
            # Cek ukuran setelah merge cepat
            check_and_compress_video(output_path)
            return True
            
        # 2. Second attempt: Re-encode (Lambat tapi Pasti Berhasil)
        logger.warning("⚠️ Merge Cepat gagal (mungkin resolusi berbeda). Mengulangi dengan Re-encode (Slow Mode)...")
        
        re_encode_command = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", list_file_path,
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            output_path
        ]
        
        process_re = subprocess.run(re_encode_command, capture_output=True, text=True)
        
        if process_re.returncode == 0:
            logger.info(f"✅ Berhasil Merge dengan Re-encode: {output_path}")
            # Cek ukuran setelah re-encode
            check_and_compress_video(output_path)
            return True
        else:
            logger.error(f"❌ SEMUA METODE MERGE GAGAL.\nError: {process_re.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"💥 Error fatal saat merge: {e}")
        return False

def check_and_compress_video(video_path: str):
    """
    Cek jika file lebih dari 1.9 GB, jika ya, kompres agar masuk limit Telegram 2GB.
    """
    try:
        size_bytes = os.path.getsize(video_path)
        limit_bytes = 1900 * 1024 * 1024 # 1.9 GB aman
        
        if size_bytes > limit_bytes:
            logger.warning(f"⚠️ File terlalu besar ({size_bytes / (1024**3):.2f} GB). Melakukan kompresi ulang agar < 2GB...")
            
            temp_compressed = video_path.replace(".mp4", "_compressed.mp4")
            # Gunakan bitrate yang lebih rendah untuk kompresi (sekitar 1.5 Mbps biasanya aman untuk total 2-3 jam)
            # -b:v 1M -maxrate 1.5M -bufsize 2M
            command = [
                "ffmpeg", "-y", "-i", video_path,
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
                "-b:v", "1200k", "-maxrate", "1800k", "-bufsize", "3000k",
                "-c:a", "aac", "-b:a", "96k",
                temp_compressed
            ]
            
            process = subprocess.run(command, capture_output=True, text=True)
            if process.returncode == 0:
                os.remove(video_path)
                os.rename(temp_compressed, video_path)
                logger.info(f"✅ Kompresi berhasil. Ukuran baru: {os.path.getsize(video_path) / (1024**3):.2f} GB")
            else:
                logger.error(f"❌ Kompresi gagal: {process.stderr}")
    except Exception as e:
        logger.error(f"Error checking size: {e}")
