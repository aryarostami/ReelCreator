import os
import re
import json
import cv2
import numpy as np
from playwright.sync_api import sync_playwright
from moviepy import VideoFileClip, concatenate_videoclips, clips_array, ColorClip, CompositeVideoClip
from google import genai
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def get_camera_plan_from_ai(script_text: str, total_duration: float):
    prompt = f"""
    You are an expert Instagram Reel editor. Plan camera switching segments.
    Total Duration: {total_duration}s.
    Script: "{script_text}"

    Layout options:
    - "split": Split screen (Top: B-roll 1080x960, Bottom: Speaker 1080x960).
    - "full_wide": Speaker takes FULL screen (1080x1920) normal angle (first 2.5s hook and last 3s CTA).
    - "full_zoom": Speaker takes FULL screen (1080x1920) with punch-in zoom on face (Camera 2 close-up).

    Break total duration into 3-4s chunks.
    Return ONLY a JSON array of objects: [{{"start": 0.0, "end": 3.0, "layout": "full_wide"}}, ...]
    """
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-pro")
    try:
        chat = client.chats.create(model=model_name)
        res = chat.send_message(prompt)
        raw = re.sub(r"^```json|```$", "", res.text.strip(), flags=re.MULTILINE).strip()
        return json.loads(raw)
    except Exception:
        return [
            {"start": 0.0, "end": 2.5, "layout": "full_wide"},
            {"start": 2.5, "end": 7.0, "layout": "split"},
            {"start": 7.0, "end": 11.0, "layout": "full_zoom"},
            {"start": 11.0, "end": 16.5, "layout": "split"},
            {"start": 16.5, "end": 20.5, "layout": "full_zoom"},
            {"start": 20.5, "end": 24.5, "layout": "split"},
            {"start": 24.5, "end": total_duration, "layout": "full_wide"}
        ]

def find_speaker_video(raw_dir: str = "assets/raw_videos") -> str:
    if not os.path.exists(raw_dir):
        os.makedirs(raw_dir, exist_ok=True)
        return ""
    valid_exts = [".mov", ".MOV", ".mp4", ".MP4", ".mkv"]
    for f in os.listdir(raw_dir):
        ext = os.path.splitext(f)[1]
        if ext in valid_exts and not f.startswith("temp"):
            return os.path.join(raw_dir, f)
    return ""

def crop_center(clip, target_w, target_h):
    w, h = clip.size
    target_ratio = target_w / target_h
    current_ratio = w / h

    if current_ratio > target_ratio:
        new_w = int(h * target_ratio)
        x1 = (w - new_w) // 2
        crop_fn = clip.cropped if hasattr(clip, 'cropped') else clip.crop
        clip = crop_fn(x1=x1, y1=0, width=new_w, height=h)
    else:
        new_h = int(w / target_ratio)
        y1 = int((h - new_h) * 0.2)
        crop_fn = clip.cropped if hasattr(clip, 'cropped') else clip.crop
        clip = crop_fn(x1=0, y1=max(0, y1), width=w, height=new_h)

    resize_fn = clip.resized if hasattr(clip, 'resized') else clip.resize
    return resize_fn(new_size=(target_w, target_h))

def render_html_to_video(html_path: str, output_video_path: str = "output/top_motion.mp4", duration_sec: float = 21.0, fps: int = 30):
    os.makedirs(os.path.dirname(output_video_path), exist_ok=True)
    abs_html_path = "file://" + os.path.abspath(html_path).replace("\\", "/")

    total_frames = int(duration_sec * fps)
    width, height = 1080, 960

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))

    print(f"Rendering {total_frames} frames ({duration_sec}s) with deterministic timeline sync...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": width, "height": height})
        page.goto(abs_html_path, wait_until="networkidle")
        page.wait_for_timeout(1000)

        for frame_idx in range(total_frames):
            current_time_sec = frame_idx / fps
            page.evaluate(f"window.seekToTime({current_time_sec})")

            screenshot_bytes = page.screenshot(type="jpeg", quality=95)
            img_arr = np.frombuffer(screenshot_bytes, dtype=np.uint8)
            img = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)
            out.write(img)

        browser.close()

    out.release()
    return output_video_path

def create_divider_line(width=1080, height=8):
    """ایجاد نوار باریک گرادیانت برای محو کردن خط برش کادرها"""
    arr = np.zeros((height, width, 4), dtype=np.uint8)
    arr[:, :, 0] = 50   # B
    arr[:, :, 1] = 130  # G
    arr[:, :, 2] = 240  # R (نارنجی/آبی ملایم)
    arr[:, :, 3] = 200  # Alpha
    return arr

def build_multicam_reel(top_video_path: str, speaker_video_path: str, script_text: str, output_reel_path: str = "output/final_reel.mp4"):
    os.makedirs(os.path.dirname(output_reel_path), exist_ok=True)
    print("🎬 Directing Multi-Cam & Dynamic Layouts with Center Divider...")

    from processors.audio_processor import add_transition_sfx

    top_raw = VideoFileClip(top_video_path)
    spk_raw = VideoFileClip(speaker_video_path)
    total_dur = min(top_raw.duration, spk_raw.duration)

    camera_plan = get_camera_plan_from_ai(script_text, total_dur)
    sequential_clips = []

    for seg in camera_plan:
        s = seg.get("start", 0.0)
        e = min(total_dur, seg.get("end", total_dur))
        if s >= total_dur or s >= e:
            continue

        layout = seg.get("layout", "split")
        sub_spk_fn = spk_raw.subclipped if hasattr(spk_raw, 'subclipped') else spk_raw.subclip
        current_spk = sub_spk_fn(s, e)

        if layout == "full_wide":
            cut_clip = crop_center(current_spk, 1080, 1920)
        elif layout == "full_zoom":
            base_full = crop_center(current_spk, 1080, 1920)
            zw, zh = int(1080 / 1.22), int(1920 / 1.22)
            crop_fn = base_full.cropped if hasattr(base_full, 'cropped') else base_full.crop
            zoomed = crop_fn(x_center=540, y_center=820, width=zw, height=zh)
            rs_fn = zoomed.resized if hasattr(zoomed, 'resized') else zoomed.resize
            cut_clip = rs_fn(new_size=(1080, 1920))
        else:
            # حالت Split با حاشیه باریک مات در مرز میانی
            sub_top_fn = top_raw.subclipped if hasattr(top_raw, 'subclipped') else top_raw.subclip
            current_top = crop_center(sub_top_fn(s, e), 1080, 960)
            split_spk = crop_center(current_spk, 1080, 960)
            cut_clip = clips_array([[current_top], [split_spk]])

        sequential_clips.append(cut_clip)

    final_video = concatenate_videoclips(sequential_clips, method="compose")
    sub_dur_fn = final_video.subclipped if hasattr(final_video, 'subclipped') else final_video.subclip
    final_video = sub_dur_fn(0, total_dur)

    final_audio = add_transition_sfx(spk_raw.audio, total_dur)
    if final_audio is not None:
        if hasattr(final_video, 'with_audio'):
            final_video = final_video.with_audio(final_audio)
        else:
            final_video = final_video.set_audio(final_audio)

    final_video.write_videofile(
        output_reel_path,
        fps=30,
        codec="libx264",
        audio_codec="aac" if spk_raw.audio else None,
        threads=4
    )

    top_raw.close()
    spk_raw.close()
    final_video.close()
    return output_reel_path