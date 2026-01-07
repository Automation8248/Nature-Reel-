import os
import requests
import random
import json
from moviepy.editor import VideoFileClip, AudioFileClip

# API Keys from GitHub Secrets
PIXABAY_KEY = os.getenv('PIXABAY_KEY')
FREESOUND_KEY = os.getenv('FREESOUND_KEY')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

def start_automation():
    # 1. Content Fetching
    page = random.randint(1, 10)
    v_api = f"https://pixabay.com/api/videos/?key={PIXABAY_KEY}&q=nature&per_page=5&page={page}"
    v_data = requests.get(v_api).json()['hits'][0]
    
    with open("video.mp4", "wb") as f:
        f.write(requests.get(v_data['videos']['large']['url']).content)
    
    # 2. Processing (9:16 Shorts)
    clip = VideoFileClip("video.mp4").subclip(0, 7.5)
    if clip.w > clip.h:
        clip = clip.crop(x1=clip.w/2 - int(clip.h*(9/16))/2, width=int(clip.h*(9/16)), height=clip.h)
    clip.resize(height=1280).write_videofile("final.mp4", codec="libx264", audio_codec="aac", fps=24)

    # 3. Upload to Catbox (For URL)
    with open("final.mp4", "rb") as f:
        upload_res = requests.post("https://catbox.moe/user/api.php", data={'reqtype': 'fileupload'}, files={'fileToUpload': f})
        video_url = upload_res.text.strip()
    
    print(f"✅ Generated URL: {video_url}")

    # 4. Sending to Webhook (CRITICAL FIX)
    if WEBHOOK_URL and "http" in video_url:
        payload = {
            "video_url": video_url,
            "caption": "Beautiful Nature Vibes 🌿 #nature #shorts"
        }
        # Headers aur JSON format ensure karte hain ki link sahi jaye
        headers = {'Content-Type': 'application/json'}
        response = requests.post(WEBHOOK_URL, data=json.dumps(payload), headers=headers)
        print(f"Webhook Status: {response.status_code}")

    # 5. Telegram (Direct File)
    with open("final.mp4", "rb") as f:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendVideo", files={'video': f}, data={'chat_id': TELEGRAM_CHAT_ID})

if __name__ == "__main__":
    start_automation()
