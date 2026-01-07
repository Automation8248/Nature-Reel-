import os
import requests
import random
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
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r") as f:
        return f.read().splitlines()

def save_history(video_id):
    with open(HISTORY_FILE, "a") as f:
        f.write(f"{str(video_id)}\n")

def get_nature_video():
    """Fetches unique nature video"""
    used_ids = load_history()
    page = random.randint(1, 20)
    url = f"https://pixabay.com/api/videos/?key={PIXABAY_KEY}&q=nature&per_page=10&page={page}"
    response = requests.get(url).json()
    hits = response.get('hits', [])
    
    selected_video = None
    for video in hits:
        if str(video['id']) not in used_ids:
            selected_video = video
            break
            
    if not selected_video:
        selected_video = random.choice(hits)

    save_history(selected_video['id'])
    
    tags = selected_video.get('tags', 'nature')
    download_url = selected_video['videos']['large']['url']
    
    print(f"Downloading Video ID: {selected_video['id']}...")
    v_content = requests.get(download_url).content
    with open("input_video.mp4", "wb") as f:
        f.write(v_content)
    
    return "input_video.mp4", tags

def get_nature_audio():
    url = f"https://freesound.org/apiv2/search/text/?query=nature&fields=id,name,previews&token={FREESOUND_KEY}&filter=duration:[10 TO 60]"
    response = requests.get(url).json()
    results = response.get('results', [])
    
    if not results:
        raise Exception("No audio found.")
    
    audio_data = random.choice(results)
    download_url = audio_data['previews']['preview-hq-mp3']
    
    print(f"Downloading Audio: {audio_data['name']}...")
    a_content = requests.get(download_url).content
    with open("input_audio.mp3", "wb") as f:
        f.write(a_content)
    return "input_audio.mp3"

def process_media(video_path, audio_path):
    print("Processing: 9:16 Crop & 7.5s Duration...")
    video_clip = VideoFileClip(video_path)
    audio_clip = AudioFileClip(audio_path)

    # 1. Fix Duration (7.5s)
    target_duration = 7.5
    if video_clip.duration < 7:
         target_duration = video_clip.duration
    
    # 2. Fix 9:16 Crop for Shorts
    target_ratio = 9/16
    current_ratio = video_clip.w / video_clip.h

    if current_ratio > target_ratio:
        new_width = int(video_clip.h * target_ratio)
        center_x = video_clip.w / 2
        video_clip = video_clip.crop(
            x1=center_x - (new_width / 2),
            y1=0,
            width=new_width,
            height=video_clip.h
        )
    
    video_clip = video_clip.resize(height=1280)
    final_video = video_clip.subclip(0, target_duration)
    
    if audio_clip.duration < target_duration:
        from moviepy.audio.fx.all import audio_loop
        final_audio = audio_loop(audio_clip, duration=target_duration)
    else:
        final_audio = audio_clip.subclip(0, target_duration)

    final_clip = final_video.set_audio(final_audio)
    
    output_filename = "final_output.mp4"
    final_clip.write_videofile(output_filename, codec="libx264", audio_codec="aac", threads=4, preset='ultrafast')
    
    return output_filename

def generate_caption(tags_string):
    """Generates Title & Hashtags"""
    raw_tags = [t.strip() for t in tags_string.split(',')]
    main_subject = raw_tags[0].title() if raw_tags else "Nature"
    
    titles = [
        f"Relaxing {main_subject} Moments 🌿",
        f"Pure {main_subject} Vibes ✨",
        f"Nature's Beauty: {main_subject} 🌍",
        f"Serene {main_subject} View 🌧️"
    ]
    title_text = random.choice(titles)

    nature_keywords = [
        "#nature", "#naturelovers", "#wildlife", "#forest", "#mountains", 
        "#ocean", "#rain", "#sky", "#flowers", "#trees", 
        "#landscape", "#earth", "#river", "#green"
    ]
    
    # Specific tags first
    video_specific = [f"#{t.replace(' ', '')}" for t in raw_tags if t.replace(' ', '').isalpha()]
    pool = list(set(video_specific + nature_keywords))
    final_tags = random.sample(pool, min(8, len(pool)))
    
    return f"{title_text}\n\n{' '.join(final_tags)}"

def upload_to_catbox(file_path):
    """Uploads to Catbox and returns URL"""
    print("Uploading to Catbox...")
    url = "https://catbox.moe/user/api.php"
    try:
        with open(file_path, "rb") as f:
            payload = {'reqtype': 'fileupload'}
            files = {'fileToUpload': f}
            response = requests.post(url, data=payload, files=files)
            
            if response.status_code == 200:
                print(f"Catbox URL: {response.text}")
                return response.text.strip()
            else:
                print(f"Catbox Error: {response.text}")
                return None
    except Exception as e:
        print(f"Catbox Connection Failed: {e}")
        return None

def send_data(file_path, caption_text):
    
    # 1. TELEGRAM (Sends File directly)
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        print("Sending File to Telegram...")
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendVideo"
        with open(file_path, 'rb') as f:
            files = {'video': ('nature_shorts.mp4', f, 'video/mp4')}
            data = {'chat_id': TELEGRAM_CHAT_ID, 'caption': caption_text}
            try:
                requests.post(url, files=files, data=data)
            except Exception as e:
                print(f"Telegram Failed: {e}")

    # 2. WEBHOOK for Make.com (Sends Link)
    if WEBHOOK_URL:
        # Step A: Get Link from Catbox
        video_link = upload_to_catbox(file_path)
        
        if video_link:
            print(f"Sending LINK to Webhook: {video_link}")
            # Step B: Send JSON Payload
            payload = {
                "video_url": video_link,
                "caption": caption_text,
                "type": "shorts"
            }
            try:
                # Use json=payload to send structured data
                r = requests.post(WEBHOOK_URL, json=payload)
                print(f"Webhook Status: {r.status_code}")
            except Exception as e:
                print(f"Webhook Failed: {e}")
        else:
            print("Skipping Webhook because Catbox upload failed.")

if __name__ == "__main__":
    try:
        v_path, v_tags = get_nature_video()
        a_path = get_nature_audio()
        final_video = process_media(v_path, a_path)
        full_caption = generate_caption(v_tags)
        
        send_data(final_video, full_caption)
        
        print("Workflow Completed!")
    except Exception as e:
        print(f"Error: {e}")
        exit(1)
