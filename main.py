import os
import requests
import random
import time
import json
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

def get_nature_video():
    print("--- Step 1: Fetching Video ---")
    used_ids = load_history()
    page = random.randint(1, 20)
    url = f"https://pixabay.com/api/videos/?key={PIXABAY_KEY}&q=nature&per_page=10&page={page}"
    
    response = requests.get(url)
    data = response.json()
    hits = data.get('hits', [])
    
    selected_video = next((v for v in hits if str(v['id']) not in used_ids), random.choice(hits) if hits else None)
    if not selected_video: raise Exception("No videos found.")

    save_history(selected_video['id'])
    v_content = requests.get(selected_video['videos']['large']['url']).content
    with open("input_video.mp4", "wb") as f: f.write(v_content)
    
    return "input_video.mp4", selected_video.get('tags', 'nature')

def get_nature_audio():
    print("--- Step 2: Fetching Audio ---")
    url = f"https://freesound.org/apiv2/search/text/?query=nature&fields=id,name,previews&token={FREESOUND_KEY}&filter=duration:[10 TO 60]"
    results = requests.get(url).json().get('results', [])
    if not results: return None
    
    audio_data = random.choice(results)
    with open("input_audio.mp3", "wb") as f:
        f.write(requests.get(audio_data['previews']['preview-hq-mp3']).content)
    return "input_audio.mp3"

def process_media(video_path, audio_path):
    print("--- Step 3: Processing Media ---")
    video_clip = VideoFileClip(video_path)
    target_duration = min(video_clip.duration, 7.5)
    
    # 9:16 Crop
    if video_clip.w / video_clip.h > 9/16:
        new_width = int(video_clip.h * (9/16))
        video_clip = video_clip.crop(x1=video_clip.w/2 - new_width/2, width=new_width, height=video_clip.h)
    
    final_video = video_clip.resize(height=1280).subclip(0, target_duration)
    
    if audio_path:
        audio_clip = AudioFileClip(audio_path).subclip(0, target_duration)
        final_video = final_video.set_audio(audio_clip)
    
    final_video.write_videofile("final_output.mp4", codec="libx264", audio_codec="aac", threads=4, preset='ultrafast')
    return "final_output.mp4"

def generate_caption(tags_string):
    raw_tags = [t.strip().replace(" ", "") for t in tags_string.split(',')]
    hashtags = " ".join([f"#{t}" for t in random.sample(raw_tags + ["nature", "forest", "peace"], min(8, len(raw_tags)+3)) if t.isalpha()])
    return f"Nature Peace 🌿\n\n{hashtags}"

def upload_to_catbox(file_path):
    print("--- Step 4: Uploading to Catbox ---")
    try:
        with open(file_path, "rb") as f:
            res = requests.post("https://catbox.moe/user/api.php", data={'reqtype': 'fileupload'}, files={'fileToUpload': f})
            if res.status_code == 200:
                url = res.text.strip()
                print(f"✅ URL Generated: {url}")
                return url
    except: return None

def send_notifications(file_path, caption_text, video_url):
    print("--- Step 5: Sending Notifications ---")
    
    # 1. Telegram (Send File)
    if TELEGRAM_TOKEN:
        with open(file_path, 'rb') as f:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendVideo", files={'video': f}, data={'chat_id': TELEGRAM_CHAT_ID, 'caption': caption_text})

    # 2. Webhook (Send URL as STRICT JSON)
    if WEBHOOK_URL and video_url:
        payload = {"video_url": video_url, "caption": caption_text}
        # json= parameter use karne se headers apne aap sahi set ho jate hain
        r = requests.post(WEBHOOK_URL, json=payload, timeout=30)
        print(f"Webhook Status: {r.status_code}, Response: {r.text}")

if __name__ == "__main__":
    try:
        v, t = get_nature_video()
        a = get_nature_audio()
        final = process_media(v, a)
        cap = generate_caption(t)
        url = upload_to_catbox(final)
        
        if url:
            send_notifications(final, cap, url)
        else:
            print("❌ Catbox fail ho gaya.")
        print("Workflow Completed!")
    except Exception as e:
        print(f"❌ Error: {e}")
