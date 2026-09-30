import os
import re
import json
from google import genai
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def get_pro_scenes_from_gemini(script_text: str, total_duration_sec: int = 28):
    # تنظیم ماندگاری حدود ۴.۵ تا ۵.۵ ثانیه برای هر B-roll تا کاربر کامل فرصت خواندن داشته باشد
    scene_duration = 5.0
    num_scenes = max(3, int(total_duration_sec // scene_duration))
    actual_duration = round(total_duration_sec / num_scenes, 2)

    prompt = f"""
    You are an elite motion designer for high-conversion Instagram reels.
    We need exactly {num_scenes} distinct, high-impact visual concepts for this script.
    Total duration: {total_duration_sec}s. Each scene lasts {actual_duration}s so users have enough time to read.
    Script: "{script_text}"

    Choose {num_scenes} formats from this pool:
    - "neon_error" (Emergency neon warning badge)
    - "crash_chart" (Aggressive downward red financial line graph)
    - "glass_funnel" (3-tier conversion funnel)
    - "speedo_gauge" (Speedometer gauge showing low trust score)
    - "terminal_cta" (Instagram comment trigger terminal)

    Return ONLY a JSON array of {num_scenes} objects with keys:
    "format" (string),
    "duration" ({actual_duration}),
    "title" (Punchy Persian label, max 4 words),
    "stat" (e.g. "0.00%", "FAIL", "89%", "کلمه سایت")
    """

    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-pro")
    for attempt in range(1, 3):
        try:
            chat = client.chats.create(model=model_name)
            res = chat.send_message(prompt)
            raw = re.sub(r"^```json|```$", "", res.text.strip(), flags=re.MULTILINE).strip()
            scenes = json.loads(raw)
            if len(scenes) == num_scenes:
                return scenes
        except Exception:
            model_name = "gemini-3.8-flash"

    # پشتیبان با ماندگاری بالا (۵ ثانیه‌ای)
    return [
        {"format": "neon_error", "duration": actual_duration, "title": "افت شدید ورودی", "stat": "NO TRAFFIC"},
        {"format": "crash_chart", "duration": actual_duration, "title": "سقوط نرخ تبدیل", "stat": "-87.4%"},
        {"format": "glass_funnel", "duration": actual_duration, "title": "ریزش کاربران در قیف", "stat": "89% DROP"},
        {"format": "speedo_gauge", "duration": actual_duration, "title": "شاخص اعتماد سایت", "stat": "LOW SCORE"},
        {"format": "terminal_cta", "duration": actual_duration, "title": "ارسال تحلیل اختصاصی", "stat": "کلمه «سایت»"}
    ][:num_scenes]

def get_format_html(sc: dict) -> str:
    fmt = sc.get("format", "neon_error")
    title = sc.get("title", "")
    stat = sc.get("stat", "")

    if fmt == "neon_error":
        return f"""
        <div class="box-neon">
            <div class="neon-warning-icon">⚠</div>
            <div class="neon-text-main">{stat}</div>
            <div class="neon-badge">{title}</div>
        </div>
        """
    elif fmt == "crash_chart":
        return f"""
        <div class="box-chart">
            <div class="chart-header">
                <span class="chart-val-down">{stat}</span>
                <span class="chart-badge-red">CRITICAL CRASH</span>
            </div>
            <svg viewBox="0 0 700 240" class="crash-svg">
                <defs>
                    <linearGradient id="redArea" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stop-color="#ef4444" stop-opacity="0.4"/>
                        <stop offset="100%" stop-color="#ef4444" stop-opacity="0.0"/>
                    </linearGradient>
                </defs>
                <path d="M 0,30 Q 150,40 300,120 T 680,220 L 680,240 L 0,240 Z" fill="url(#redArea)"/>
                <path d="M 0,30 Q 150,40 300,120 T 680,220" fill="none" stroke="#ef4444" stroke-width="8" stroke-linecap="round"/>
                <circle cx="670" cy="220" r="10" fill="#ef4444" class="crash-dot"/>
            </svg>
            <div class="chart-title">{title}</div>
        </div>
        """
    elif fmt == "glass_funnel":
        return f"""
        <div class="box-funnel">
            <div class="funnel-level f-top"><span>ورودی کل</span><strong>10,000</strong></div>
            <div class="funnel-level f-mid"><span>اعتماد به سایت</span><strong>1,200</strong></div>
            <div class="funnel-level f-btm"><span>خرید نهایی</span><strong>{stat}</strong></div>
            <div class="funnel-title-tag">{title}</div>
        </div>
        """
    elif fmt == "speedo_gauge":
        return f"""
        <div class="box-gauge">
            <div class="gauge-arc">
                <div class="gauge-needle"></div>
                <div class="gauge-center"></div>
            </div>
            <div class="gauge-val-tag">{stat}</div>
            <div class="gauge-title-tag">{title}</div>
        </div>
        """
    else:
        return f"""
        <div class="box-cta">
            <div class="cta-topbar">
                <span class="c-dot rd"></span><span class="c-dot yl"></span><span class="c-dot gr"></span>
                <span class="cta-console-name">AUDIT_BOT.exe</span>
            </div>
            <div class="cta-body">
                <div class="cta-instruction">> جهت دریافت رایگان چک‌لیست عیب‌یابی:</div>
                <div class="cta-keyword-box"><span class="cursor-blink">|</span> {stat}</div>
                <div class="cta-subtitle">{title}</div>
            </div>
        </div>
        """

def build_top_broll_html(script_text: str, total_duration_sec: int = 28, output_folder: str = "temp"):
    os.makedirs(output_folder, exist_ok=True)
    html_path = os.path.join(output_folder, "top_motion.html")

    scenes = get_pro_scenes_from_gemini(script_text, total_duration_sec)

    slides_data = []
    for idx, sc in enumerate(scenes):
        slides_data.append({
            "id": idx,
            "duration": sc.get("duration", 5.0),
            "markup": get_format_html(sc)
        })

    full_html = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    html, body {{
        width: 1080px; height: 960px; overflow: hidden;
        background: #020408;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Vazirmatn", Tahoma, sans-serif;
    }}
    .stage {{
        width: 1080px; height: 960px; position: relative;
        background: #030712;
    }}
    .slide {{
        position: absolute; inset: 0;
        width: 1080px; height: 960px;
        display: flex; justify-content: center; align-items: center;
        opacity: 0; transform: scale(0.95);
        transition: opacity 0.35s ease-out, transform 0.35s ease-out;
        pointer-events: none;
    }}
    .slide.active {{
        opacity: 1; transform: scale(1);
        pointer-events: auto;
    }}

    .box-neon {{
        width: 860px; border-radius: 40px; background: #0c0507;
        border: 4px solid #ef4444; box-shadow: 0 0 70px rgba(239, 68, 68, 0.4), inset 0 0 30px rgba(239, 68, 68, 0.2);
        display: flex; flex-direction: column; align-items: center; justify-content: center;
        padding: 60px; gap: 24px;
    }}
    .neon-warning-icon {{ font-size: 110px; color: #ef4444; text-shadow: 0 0 30px #ef4444; }}
    .neon-text-main {{ font-size: 80px; font-weight: 900; color: #ffffff; letter-spacing: 4px; }}
    .neon-badge {{ font-size: 36px; font-weight: 800; color: #fca5a5; background: rgba(239,68,68,0.2); padding: 12px 36px; border-radius: 100px; }}

    .box-chart {{
        width: 900px; background: #0b0f19; border: 2px solid #1e293b; border-radius: 36px;
        padding: 45px; display: flex; flex-direction: column; gap: 24px; box-shadow: 0 30px 60px rgba(0,0,0,0.7);
    }}
    .chart-header {{ display: flex; justify-content: space-between; align-items: center; }}
    .chart-val-down {{ font-size: 76px; font-weight: 900; color: #ef4444; }}
    .chart-badge-red {{ background: rgba(239,68,68,0.15); color: #f87171; border: 1px solid #ef4444; font-size: 24px; font-weight: 800; padding: 8px 24px; border-radius: 12px; }}
    .crash-svg {{ width: 100%; height: 200px; }}
    .crash-dot {{ animation: pulseDot 0.8s infinite alternate; }}
    @keyframes pulseDot {{ 50% {{ transform: scale(1.4); }} }}
    .chart-title {{ font-size: 40px; font-weight: 800; color: #cbd5e1; text-align: center; }}

    .box-funnel {{ width: 880px; display: flex; flex-direction: column; align-items: center; gap: 20px; }}
    .funnel-level {{
        height: 80px; border-radius: 20px; display: flex; align-items: center; justify-content: space-between;
        padding: 0 40px; font-size: 28px; font-weight: 800; color: #ffffff; box-shadow: 0 10px 25px rgba(0,0,0,0.4);
    }}
    .f-top {{ width: 880px; background: linear-gradient(90deg, #2563eb, #1d4ed8); }}
    .f-mid {{ width: 620px; background: linear-gradient(90deg, #6366f1, #4f46e5); }}
    .f-btm {{ width: 380px; background: linear-gradient(90deg, #db2777, #be185d); }}
    .funnel-title-tag {{ font-size: 40px; font-weight: 900; color: #f8fafc; margin-top: 15px; }}

    .box-gauge {{ display: flex; flex-direction: column; align-items: center; gap: 24px; }}
    .gauge-arc {{
        width: 440px; height: 220px; border-top-left-radius: 220px; border-top-right-radius: 220px;
        border: 30px solid #1e293b; border-bottom: none; position: relative;
        background: radial-gradient(circle at bottom, rgba(234, 179, 8, 0.15) 0%, transparent 70%);
    }}
    .gauge-needle {{
        position: absolute; bottom: 0; left: 50%; width: 6px; height: 160px; background: #eab308;
        transform-origin: bottom center; transform: rotate(-65deg); border-radius: 6px; box-shadow: 0 0 20px #eab308;
    }}
    .gauge-center {{ position: absolute; bottom: -15px; left: 50%; transform: translateX(-50%); width: 30px; height: 30px; border-radius: 50%; background: #ffffff; }}
    .gauge-val-tag {{ font-size: 60px; font-weight: 900; color: #eab308; }}
    .gauge-title-tag {{ font-size: 40px; font-weight: 800; color: #cbd5e1; }}

    .box-cta {{
        width: 880px; background: #0b0f19; border: 3px solid #facc15; border-radius: 36px;
        box-shadow: 0 0 60px rgba(250, 204, 21, 0.3); overflow: hidden;
    }}
    .cta-topbar {{ background: #1e293b; padding: 18px 24px; display: flex; align-items: center; gap: 10px; }}
    .c-dot {{ width: 16px; height: 16px; border-radius: 50%; }}
    .rd {{ background: #ef4444; }} .yl {{ background: #eab308; }} .gr {{ background: #22c55e; }}
    .cta-console-name {{ margin-right: 15px; font-family: monospace; font-size: 20px; color: #94a3b8; }}
    .cta-body {{ padding: 50px 40px; display: flex; flex-direction: column; align-items: center; gap: 24px; text-align: center; }}
    .cta-instruction {{ font-size: 32px; font-weight: 700; color: #cbd5e1; }}
    .cta-keyword-box {{
        background: #020617; border: 2px solid #facc15; border-radius: 24px;
        padding: 20px 60px; font-size: 70px; font-weight: 900; color: #facc15;
        box-shadow: 0 0 35px rgba(250, 204, 21, 0.3);
    }}
    .cursor-blink {{ animation: blink 0.8s infinite; color: #facc15; }}
    .cta-subtitle {{ font-size: 34px; font-weight: 700; color: #94a3b8; }}
    @keyframes blink {{ 50% {{ opacity: 0; }} }}
</style>
</head>
<body>
<div class="stage">
    {''.join([f'<div class="slide" id="slide-{i}">{s["markup"]}</div>' for i, s in enumerate(slides_data)])}
</div>

<script>
    const timeline = {json.dumps(slides_data)};
    window.seekToTime = function(sec) {{
        let acc = 0; let activeIdx = 0;
        for (let i = 0; i < timeline.length; i++) {{
            acc += timeline[i].duration;
            if (sec < acc) {{ activeIdx = i; break; }}
            if (i === timeline.length - 1) {{ activeIdx = i; }}
        }}
        document.querySelectorAll('.slide').forEach((el, idx) => {{
            el.classList.toggle('active', idx === activeIdx);
        }});
    }};
    window.seekToTime(0);
</script>
</body>
</html>
"""
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(full_html)

    return html_path, total_duration_sec