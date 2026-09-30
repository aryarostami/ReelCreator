
import os
import random
from moviepy import AudioFileClip, CompositeAudioClip

def add_transition_sfx(base_audio, total_duration: float, sfx_dir: str = "assets/audio"):
    """میکس افکت‌های صوتی Whoosh و Sweep در هر ۳ ثانیه کات تصویر"""
    if not os.path.exists(sfx_dir):
        return base_audio

    # انتخاب فایل‌های سالم ترنزیشن
    valid_sfx = [
        "mixkit-cinematic-whoosh-fast-transition-1492.wav",
        "mixkit-fast-small-sweep-transition-166.wav",
        "mixkit-fast-whoosh-transition-1490.wav",
        "mixkit-short-transition-sweep-175.wav"
    ]
    
    audio_clips = []
    if base_audio is not None:
        audio_clips.append(base_audio)

    # قرار دادن افکت صوتی در هر کات (هر ۳ ثانیه)
    cut_timestamps = [i for i in range(3, int(total_duration), 3)]
    for ts in cut_timestamps:
        sfx_file = random.choice(valid_sfx)
        sfx_path = os.path.join(sfx_dir, sfx_file)
        if os.path.exists(sfx_path):
            try:
                sfx_clip = AudioFileClip(sfx_path)
                # کاهش ولوم ترنزیشن به ۳۰ درصد تا صدای گوینده واضح بماند
                sfx_clip = sfx_clip.with_volume_scaled(0.3) if hasattr(sfx_clip, 'with_volume_scaled') else sfx_clip.volumex(0.3)
                sfx_clip = sfx_clip.with_start(ts) if hasattr(sfx_clip, 'with_start') else sfx_clip.set_start(ts)
                audio_clips.append(sfx_clip)
            except Exception as e:
                print(f"Notice on sfx loading: {e}")

    if audio_clips:
        return CompositeAudioClip(audio_clips)
    return base_audio