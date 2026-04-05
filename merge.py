import os
import subprocess
import logging

logger = logging.getLogger(__name__)

def merge_episodes(video_dir: str, output_path: str):
    """
    Merges all .mp4 files in video_dir into a single output_path file.
    video_dir: Directory containing episode_.mp4 files.
    output_path: Path for final merged video.
    """
    try:
        # Get all video files in numeric order
        files = [f for f in os.listdir(video_dir) if f.endswith(".mp4")]
        files.sort() # Sorted alphabetically/numerically like episode_001.mp4
        
        list_file_path = os.path.join(video_dir, "list.txt")
        with open(list_file_path, "w") as f:
            for file in files:
                f.write(f"file '{file}'\n")

        # ffmpeg -f concat -safe 0 -i list.txt -c copy output.mp4
        command = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", list_file_path,
            "-c", "copy",
            output_path
        ]
        
        logger.info(f"Running ffmpeg merge command (fast copy): {' '.join(command)}")
        
        # 1. First attempt: -c copy (Very Fast)
        process = subprocess.run(command, capture_output=True, text=True, cwd=video_dir)
        if process.returncode == 0:
            logger.info(f"Successfully merged episodes (copy) into {output_path}")
            return True
            
        # 2. Second attempt: Re-encode (Slow but reliable)
        logger.warning(f"Fast merge failed (likely resolution mismatch), retrying with re-encode...")
        re_encode_command = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", list_file_path,
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23", "-c:a", "aac",
            output_path
        ]
        logger.info(f"Running ffmpeg merge command (re-encode): {' '.join(re_encode_command)}")
        process_re = subprocess.run(re_encode_command, capture_output=True, text=True, cwd=video_dir)
        
        if process_re.returncode == 0:
            logger.info(f"Successfully merged episodes (re-encode) into {output_path}")
            return True
        else:
            logger.error(f"FFmpeg re-encode merge failed with error:\n{process_re.stderr}")
            return False
    except Exception as e:
        logger.error(f"Error during merge: {e}")
        return False
