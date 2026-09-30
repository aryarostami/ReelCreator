import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from moviepy import VideoFileClip
from generators.script_generator import build_top_broll_html
from processors.video_processor import render_html_to_video, build_multicam_reel, find_speaker_video
from processors.speaker_enhancer import process_raw_speaker

def read_script_file(file_path: str = "script.txt") -> str:
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read().strip()

def run_pipeline(speaker_path: str = None, script_text: str = None, output_path: str = "output/final_reel.mp4"):
    print("=" * 60)
    print("🎬 STARTING PRO AUTOMATED REEL PIPELINE")

    if not speaker_path:
        speaker_path = find_speaker_video("assets/raw_videos")
    
    if not speaker_path or not os.path.exists(speaker_path):
        print("Error: No speaker video found!")
        return None

    # ۱. برش هوشمند سکوت‌ها
    enhanced_speaker = process_raw_speaker(speaker_path, "temp/enhanced_speaker.mp4")
    with VideoFileClip(enhanced_speaker) as spk:
        duration_sec = int(spk.duration)
    print(f"Final active speech duration: {duration_sec}s")

    # ۲. خواندن سناریو و تولید B-roll ماندگار
    if not script_text:
        script_text = read_script_file("script.txt")

    html_file, dur = build_top_broll_html(script_text, total_duration_sec=duration_sec)

    # ۳. رندر فریم‌های متحرک بالا
    top_video = render_html_to_video(html_file, output_video_path="output/top_motion.mp4", duration_sec=dur)

    # ۴. تدوین چند دوربینه با کات‌های نرم
    final_reel = build_multicam_reel(
        top_video_path=top_video,
        speaker_video_path=enhanced_speaker,
        script_text=script_text,
        output_reel_path=output_path
    )

    print("=" * 60)
    print(f"✅ Master Reel Ready for Instagram: {final_reel}")
    print("=" * 60)
    return final_reel

if __name__ == "__main__":
    run_pipeline()