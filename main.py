import os
import requests
import random
import json
import time
from moviepy.editor import VideoFileClip, AudioFileClip

# --- CONFIGURATION ---
PIXABAY_KEY = os.getenv('PIXABAY_KEY')
FREESOUND_KEY = os.getenv('FREESOUND_KEY')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
HISTORY_FILE = "history.txt"

def load_history():
    if not os.path.exists(HISTORY_FILE): return []
    with open(HISTORY_FILE, "r") as f: return f.read().splitlines()

def save_history(video_id):
    with open(HISTORY_FILE, "a") as f: f.write(f"{str(video_id)}\n")

# 1. FETCH CONTENT
def get_nature_content():
    print(">>> Step 1: Fetching nature content...")
    used_ids = load_history()
    page = random.randint(1, 15)
    
    v_url = f"https://pixabay.com/api/videos/?key={PIXABAY_KEY}&q=nature&per_page=10&page={page}"
    v_res = requests.get(v_url).json().get('hits', [])
    video = next((v for v in v_res if str(v['id']) not in used_ids), random.choice(v_res) if v_res else None)
    
    if not video: raise Exception("No Video found on Pixabay.")
    save_history(video['id'])
    
    with open("input.mp4", "wb") as f: f.write(requests.get(video['videos']['large']['url']).content)
    
    try:
        a_url = f"https://freesound.org/apiv2/search/text/?query=nature&fields=id,previews&token={FREESOUND_KEY}&filter=duration:[10 TO 60]"
        a_res = requests.get(a_url).json().get('results', [])
        if a_res:
            with open("input.mp3", "wb") as f: f.write(requests.get(random.choice(a_res)['previews']['preview-hq-mp3']).content)
    except: pass # Silent if audio fails
    
    return "input.mp4", "input.mp3" if os.path.exists("input.mp3") else None, video.get('tags', 'nature')

# 2. PROCESS VIDEO (Shorts 9:16)
def process_video(v, a):
    print(">>> Step 2: Processing 9:16 Shorts (7.5s)...")
    clip = VideoFileClip(v)
    duration = min(clip.duration, 7.5)
    
    if clip.w / clip.h > 9/16:
        new_w = int(clip.h * (9/16))
        clip = clip.crop(x1=clip.w/2 - new_w/2, width=new_w, height=clip.h)
    
    clip = clip.resize(height=1280).subclip(0, duration)
    if a:
        clip = clip.set_audio(AudioFileClip(a).subclip(0, duration))
        
    clip.write_videofile("final.mp4", codec="libx264", audio_codec="aac", threads=4, preset='ultrafast')
    return "final.mp4"

# 3. GENERATE CAPTION
def generate_caption(tags):
    raw = [t.strip().replace(" ", "") for t in tags.split(',')]
    pool = list(set(["#"+t for t in raw if t.isalpha()] + ["#nature", "#forest", "#serene", "#earth"]))
    hashtags = " ".join(random.sample(pool, min(8, len(pool))))
    return f"Peaceful Nature Vibes 🌿\n\n{hashtags}"

# 4. SEND CONTENT
def send_results(file, cap):
    print(">>> Step 3: Sending to Telegram and Webhook...")
    
    # Telegram (File)
    if TELEGRAM_TOKEN:
        with open(file, 'rb') as f:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendVideo", 
                          files={'video': f}, data={'chat_id': TELEGRAM_CHAT_ID, 'caption': cap})
        print("✅ Telegram Sent")

    # Webhook (Link)
    if WEBHOOK_URL:
        with open(file, "rb") as f:
            res = requests.post("https://catbox.moe/user/api.php", data={'reqtype': 'fileupload'}, files={'fileToUpload': f})
        
        if res.status_code == 200:
            v_url = res.text.strip()
            print(f"✅ Catbox URL: {v_url}")
            # JSON Payload for Make.com
            payload = {"video_url": v_url, "caption": cap}
            requests.post(WEBHOOK_URL, json=payload)
            print("✅ Webhook Sent with URL")
        else:
            print("❌ Catbox Upload Failed")

if __name__ == "__main__":
    try:
        v, a, t = get_nature_content()
        final = process_video(v, a)
        caption = generate_caption(t)
        send_results(final, caption)
        print("SUCCESS")
    except Exception as e:
        print(f"ERROR: {e}")
        exit(1)
