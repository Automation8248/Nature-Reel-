import os
import requests
import random
import json
import time
from moviepy.editor import VideoFileClip, AudioFileClip

# Secrets
PIXABAY_KEY = os.getenv('PIXABAY_KEY')
FREESOUND_KEY = os.getenv('FREESOUND_KEY')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

def run_project():
    # 1. Video & Audio Fetch
    v_res = requests.get(f"https://pixabay.com/api/videos/?key={PIXABAY_KEY}&q=nature&per_page=5").json()['hits'][0]
    with open("v.mp4", "wb") as f: f.write(requests.get(v_res['videos']['large']['url']).content)
    
    # 2. Processing (Shorts 9:16)
    clip = VideoFileClip("v.mp4").subclip(0, 7.5)
    if clip.w > clip.h:
        new_w = int(clip.h * (9/16))
        clip = clip.crop(x1=clip.w/2 - new_w/2, width=new_w, height=clip.h)
    clip.resize(height=1280).write_videofile("final.mp4", codec="libx264", audio_codec="aac", fps=24)

    # 3. Catbox Upload (Yahan URL banta hai)
    print(">>> Uploading to Catbox...")
    with open("final.mp4", "rb") as f:
        res = requests.post("https://catbox.moe/user/api.php", data={'reqtype': 'fileupload'}, files={'fileToUpload': f})
        video_url = res.text.strip()
    
    # LOG: Agar ye print nahi hua, toh upload fail hua hai
    print(f"✅ FINAL VIDEO URL: {video_url}")

    # 4. Webhook par Data bhejna (FIXED PAYLOAD)
    if WEBHOOK_URL and "https://" in video_url:
        # Hum JSON format mein bhej rahe hain
        payload = {
            "video_url": video_url,
            "caption": "Nature Vibes 🌿 #nature #shorts",
            "status": "success"
        }
        headers = {'Content-Type': 'application/json'}
        r = requests.post(WEBHOOK_URL, data=json.dumps(payload), headers=headers)
        print(f">>> Webhook Status: {r.status_code}")
    else:
        print("❌ URL missing, Webhook nahi bheja gaya.")

    # 5. Telegram (File bhejna)
    with open("final.mp4", "rb") as f:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendVideo", files={'video': f}, data={'chat_id': TELEGRAM_CHAT_ID})

if __name__ == "__main__":
    run_project()
