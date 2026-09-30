import os
import subprocess
import whisper

EMPHASIS_KEYWORDS = [
    "سایت", "سایتت", "مشتری", "فروش", "سقوط", "مشکل", "اشتباه", "پول", "ترافیک",
    "سئو", "آنالیز", "نتیجه", "تبدیل", "عالی", "رایگان", "چک‌لیست", "دایرکت", "کامنت"
]

def transcribe_audio_words(audio_or_video_path: str):
    print("=" * 60)
    print("🎙 TRANSCRIBING PERSIAN SPEECH (WORD-BY-WORD WHISPER)...")
    
    model = whisper.load_model("base")
    result = model.transcribe(audio_or_video_path, language="fa", word_timestamps=True)

    words = []
    for segment in result.get("segments", []):
        for w in segment.get("words", []):
            word_text = w.get("word", "").strip()
            if word_text:
                words.append({
                    "word": word_text,
                    "start": round(w.get("start", 0.0), 2),
                    "end": round(w.get("end", 0.0), 2),
                    "is_emphasis": any(k in word_text for k in EMPHASIS_KEYWORDS)
                })
    return words

def generate_subtitles_ass(words: list, total_duration: float, output_ass: str = "temp/karaoke.ass"):
    os.makedirs(os.path.dirname(output_ass), exist_ok=True)

    # فونت‌های استاندارد ویندوز که حروف فارسی را بی‌‌نقص نمایش می‌دهند
    font_name = "Segoe UI"

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},58,&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,5,3,2,60,60,540,1
Style: ActiveWord,{font_name},66,&H0000E6FF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,6,4,2,60,60,540,1
Style: EmphasisWord,{font_name},78,&H0022FF22,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,115,115,0,0,1,7,5,2,60,60,540,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    chunks = []
    chunk_size = 4
    for i in range(0, len(words), chunk_size):
        group = words[i:i + chunk_size]
        if group:
            chunks.append(group)

    events = []
    for grp in chunks:
        def fmt_time(sec):
            h = int(sec // 3600)
            m = int((sec % 3600) // 60)
            s = int(sec % 60)
            cs = int((sec % 1) * 100)
            return f"{h:01d}:{m:02d}:{s:02d}.{cs:02d}"

        for current_word in grp:
            w_start = current_word["start"]
            w_end = current_word["end"]
            
            line_parts = []
            for w in grp:
                txt = w["word"]
                if w == current_word:
                    if w["is_emphasis"]:
                        line_parts.append(r"{\rEmphasisWord\c&H0022FF22&}" + txt + r"{\r}")
                    else:
                        line_parts.append(r"{\rActiveWord\c&H0000E6FF&}" + txt + r"{\r}")
                else:
                    line_parts.append(r"{\c&H00FFFFFF&}" + txt)

            formatted_text = " ".join(line_parts)
            events.append(f"Dialogue: 0,{fmt_time(w_start)},{fmt_time(w_end)},Default,,0,0,0,,{formatted_text}")

    with open(output_ass, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(events))

    return output_ass

def burn_subtitles_to_video(input_video: str, ass_path: str, output_video: str = "output/final_reel.mp4"):
    print("🔥 BURNING DYNAMIC PERSIAN KARAOKE SUBTITLES...")
    # فرمت آدرس‌دهی امن برای ویندوز در فیلتر FFmpeg
    abs_ass = os.path.abspath(ass_path).replace("\\", "/").replace(":", "\\:")

    cmd = [
        "ffmpeg", "-y",
        "-i", input_video,
        "-vf", f"subtitles='{abs_ass}'",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18",
        "-c:a", "copy",
        output_video
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return output_video if os.path.exists(output_video) else input_video