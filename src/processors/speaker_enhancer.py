import os
import subprocess
import numpy as np
import torch

def get_video_duration(file_path: str) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        return float(res.stdout.strip())
    except Exception:
        return 0.0

def load_audio_tensor_raw(video_path: str, temp_pcm: str = "temp/speech_16k.raw"):
    """استخراج مستقیم دیتای صوتی 16kHz Float32 بدون نیاز به torchaudio"""
    os.makedirs(os.path.dirname(temp_pcm), exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vn", "-ac", "1", "-ar", "16000",
        "-f", "f32le",
        temp_pcm
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if not os.path.exists(temp_pcm) or os.path.getsize(temp_pcm) == 0:
        return None

    # خواندن آرایه فلوت ۳۲ به صورت مستقیم و انتقال به تنسور
    audio_data = np.fromfile(temp_pcm, dtype=np.float32)
    return torch.from_numpy(audio_data)

def extract_speech_timestamps_vad(video_path: str):
    wav_tensor = load_audio_tensor_raw(video_path)
    if wav_tensor is None:
        return []

    try:
        from silero_vad import load_silero_vad, get_speech_timestamps
        model = load_silero_vad()

        # تنظیمات بر مبنای برش تهاجمی سکوت‌های ریلزی:
        # هر مکث بالای ۲۰۰ میلی‌ثانیه کاملاً حذف می‌شود
        speech_timestamps = get_speech_timestamps(
            wav_tensor,
            model,
            threshold=0.30,             # حساسیت به کلام
            min_silence_duration_ms=200, # مکث‌های بیشتر از 0.2 ثانیه کات می‌شوند
            speech_pad_ms=60            # بافر نرم 60 میلی‌ثانیه‌ای برای کلمات
        )

        intervals = []
        for ts in speech_timestamps:
            start_sec = round(ts['start'] / 16000, 3)
            end_sec = round(ts['end'] / 16000, 3)
            # فقط بخش‌های گفتاری با طول منطقی
            if end_sec - start_sec > 0.15:
                intervals.append((start_sec, end_sec))

        return intervals
    except Exception as e:
        print(f"Neural scan notice: {e}")
        return []

def process_raw_speaker(input_video_path: str, output_video_path: str = "temp/enhanced_speaker.mp4") -> str:
    os.makedirs(os.path.dirname(output_video_path), exist_ok=True)
    orig_dur = get_video_duration(input_video_path)
    print("=" * 60)
    print("🧠 RUNNING NEURAL SILERO-VAD SPEECH DETECTOR (ZERO-DEPENDENCY)...")

    intervals = extract_speech_timestamps_vad(input_video_path)

    if not intervals or len(intervals) <= 1:
        print("VAD detected continuous speech or failed to split segments.")
        return input_video_path

    # تولید فیلتر اتصال بخش‌های گفتاری (Jump-cuts)
    filter_parts = []
    concat_inputs = ""
    for i, (start, end) in enumerate(intervals):
        filter_parts.append(f"[0:v]trim=start={start}:end={end},setpts=PTS-STARTPTS[v{i}];")
        # اعمال دینویز هوشمند همزمان با کات
        filter_parts.append(f"[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS,highpass=f=80,afftdn=nr=18:nf=-35[a{i}];")
        concat_inputs += f"[v{i}][a{i}]"

    filter_complex = "".join(filter_parts) + f"{concat_inputs}concat=n={len(intervals)}:v=1:a=1[outv][outa]"

    cmd = [
        "ffmpeg", "-y",
        "-i", input_video_path,
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-map", "[outa]",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        output_video_path
    ]

    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if proc.returncode == 0 and os.path.exists(output_video_path):
            new_dur = get_video_duration(output_video_path)
            saved = orig_dur - new_dur
            print(f"✅ VAD Success! Detected {len(intervals)} speech chunks (Jump-cuts: {len(intervals)-1})")
            print(f"⏱ Video Trimmed: {round(orig_dur, 2)}s -> {round(new_dur, 2)}s (Removed {round(saved, 2)}s silence)")
            return output_video_path
        else:
            print("FFmpeg error trace:", proc.stderr[:300])
    except Exception as e:
        print("Trim execution notice:", e)

    return input_video_path