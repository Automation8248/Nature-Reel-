import os
import requests
import random
import json
import time

# --- CONFIGURATION ---
PIXABAY_KEY = os.getenv('PIXABAY_KEY')
FREESOUND_KEY = os.getenv('FREESOUND_KEY')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
HISTORY_FILE = "history.txt"

# --- LIBRARY CHECK ---
try:
    from moviepy.editor import VideoFileClip, AudioFileClip
except ImportError:
    print("CRITICAL ERROR: 'moviepy' library failed. Check requirements.txt has 'moviepy==1.0.3'")
    exit(1)

def load_history():
    if not os.path.exists(HISTORY_FILE): return []
    with open(HISTORY_FILE, "r") as f: return f.read().splitlines()

def save_history(video_id):
    with open(HISTORY_FILE, "a") as f: f.write(f"{str(video_id)}\n")

# 1. DOWNLOAD CONTENT
def get_content():
    print(">>> STEP 1: Content Download...")
    used_ids = load_history()
    page = random.randint(1, 10)
    
    # Fetch Video
    v_url = f"https://pixabay.com/api/videos/?key={PIXABAY_KEY}&q=nature&per_page=10&page={page}"
    try:
        response = requests.get(v_url)
        response.raise_for_status()
        hits = response.json().get('hits', [])
        
        # Select unique video
        video = next((v for v in hits if str(v['id']) not in used_ids), None)
        if not video and hits: video = random.choice(hits)
        if not video: raise Exception("No Video Found")
        
        save_history(video['id'])
        print(f"   - Video ID: {video['id']}")
        
        v_data = requests.get(video['videos']['large']['url']).content
        with open("input_video.mp4", "wb") as f: f.write(v_data)
        tags = video.get('tags', 'nature')
    except Exception as e:
        raise Exception(f"Pixabay Error: {e}")

    # Fetch Audio
    try:
        a_url = f"https://freesound.org/apiv2/search/text/?query=nature&fields=id,name,previews&token={FREESOUND_KEY}&filter=duration:[10 TO 60]"
        results = requests.get(a_url).json().get('results', [])
        if results:
            track = random.choice(results)
            print(f"   - Audio: {track['name']}")
            a_data = requests.get(track['previews']['preview-hq-mp3']).content
            with open("input_audio.mp3", "wb") as f: f.write(a_data)
    except: 
        print("   - Audio fetch failed (Silent video will be used)")

    return "input_video.mp4", "input_audio.mp3" if os.path.exists("input_audio.mp3") else None, tags

# 2. EDIT VIDEO
def process_video(v_path, a_path):
    print(">>> STEP 2: Editing Video (9:16 Shorts)...")
    clip = VideoFileClip(v_path)
    
    # Duration Logic (Max 7.5s)
    duration = min(clip.duration, 7.5)
    
    # 9:16 Crop Logic
    w, h = clip.size
    target_ratio = 9/16
    current_ratio = w / h

    if current_ratio > target_ratio:
        # Too wide, crop the sides
        new_width = int(h * target_ratio)
        center_x = w / 2
        clip = clip.crop(x1=center_x - new_width/2, y1=0, width=new_width, height=h)
    
    # Resize and Trim
    clip = clip.resize(height=1280).subclip(0, duration)
    
    # Add Audio
    if a_path:
        audio = AudioFileClip(a_path).subclip(0, duration)
        clip = clip.set_audio(audio)
        
    output_path = "final_output.mp4"
    clip.write_videofile(output_path, codec="libx264", audio_codec="aac", threads=4, preset='ultrafast')
    return output_path

# 3. GENERATE CAPTION
def get_caption(tags):
    keywords = [t.strip().replace(" ", "") for t in tags.split(',')]
    safe_tags = [f"#{k}" for k in keywords if k.isalpha()]
    nature_tags = ["#nature", "#wildlife", "#green", "#peace", "#earth", "#forest"]
    
    # Combine and pick 8
    pool = list(set(safe_tags + nature_tags))
    final_tags = random.sample(pool, min(8, len(pool)))
    
    return f"Nature Vibes 🌿\n\n{' '.join(final_tags)}"

# 4. UPLOAD & SEND
def distribute_content(file_path, caption):
    print(">>> STEP 3: Uploading & Distributing...")
    
    # A. Send to Telegram (Video File)
    if TELEGRAM_TOKEN:
        print("   - Sending File to Telegram...")
        with open(file_path, 'rb') as f:
            try:
                requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendVideo",
                    files={'video': f},
                    data={'chat_id': TELEGRAM_CHAT_ID, 'caption': caption}
                )
            except Exception as e:
                print(f"Telegram Error: {e}")

    # B. Send to Webhook (Video URL)
    if WEBHOOK_URL:
        print("   - Uploading to Catbox for Webhook URL...")
        try:
            with open(file_path, "rb") as f:
                response = requests.post(
                    "https://catbox.moe/user/api.php",
                    data={'reqtype': 'fileupload'},
                    files={'fileToUpload': f}
                )
            
            if response.status_code == 200:
                video_url = response.text.strip()
                print(f"   ✅ URL Generated: {video_url}")
                
                # Send JSON Payload to Make.com
                payload = {
                    "video_url": video_url,
                    "caption": caption,
                    "status": "ready"
                }
                headers = {'Content-Type': 'application/json'}
                
                r = requests.post(WEBHOOK_URL, json=payload, headers=headers)
                print(f"   ✅ Webhook Sent! Status: {r.status_code}")
            else:
                print(f"   ❌ Catbox Upload Failed: {response.text}")
        except Exception as e:
            print(f"   ❌ Webhook/Upload Error: {e}")

if __name__ == "__main__":
    try:
        v, a, t = get_content()
        final = process_video(v, a)
        cap = get_caption(t)
        distribute_content(final, cap)
        print(">>> SUCCESS: Workflow Completed.")
    except Exception as e:
        print(f"❌ FATAL ERROR: {e}")
        exit(1)
