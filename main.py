import os
import requests
import random
from moviepy.editor import VideoFileClip, AudioFileClip

# --- CONFIGURATION ---
PIXABAY_KEY = os.getenv('PIXABAY_KEY')
FREESOUND_KEY = os.getenv('FREESOUND_KEY')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
HISTORY_FILE = "history.txt"

def load_history():
    """Purane used video IDs load karega"""
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r") as f:
        return f.read().splitlines()

def save_history(video_id):
    """New video ID ko history file mein save karega"""
    with open(HISTORY_FILE, "a") as f:
        f.write(f"{str(video_id)}\n")

def get_nature_video():
    """Fetches unique nature video from Pixabay"""
    used_ids = load_history()
    
    # Random page 1 to 20 to get variety
    page = random.randint(1, 20)
    url = f"https://pixabay.com/api/videos/?key={PIXABAY_KEY}&q=nature&per_page=10&page={page}"
    response = requests.get(url).json()
    hits = response.get('hits', [])
    
    selected_video = None
    
    # Check for duplicate
    for video in hits:
        if str(video['id']) not in used_ids:
            selected_video = video
            break
            
    if not selected_video:
        # Agar saare used hain, toh random utha lo (fallback)
        print("Warning: All videos on this page used, picking random.")
        selected_video = random.choice(hits)

    # Save ID immediately locally
    save_history(selected_video['id'])
    
    download_url = selected_video['videos']['large']['url'] # 1080p or 720p
    print(f"Downloading video ID: {selected_video['id']}...")
    
    v_content = requests.get(download_url).content
    with open("input_video.mp4", "wb") as f:
        f.write(v_content)
    
    return "input_video.mp4"

def get_nature_audio():
    """Fetches random nature sound"""
    url = f"https://freesound.org/apiv2/search/text/?query=nature&fields=id,name,previews&token={FREESOUND_KEY}&filter=duration:[10 TO 60]"
    response = requests.get(url).json()
    results = response.get('results', [])
    
    if not results:
        raise Exception("No audio found.")
    
    audio_data = random.choice(results)
    download_url = audio_data['previews']['preview-hq-mp3']
    
    print(f"Downloading audio: {audio_data['name']}...")
    a_content = requests.get(download_url).content
    with open("input_audio.mp3", "wb") as f:
        f.write(a_content)
    return "input_audio.mp3"

def process_media(video_path, audio_path):
    """Combines and Trims to 7-8 Seconds"""
    print("Processing media...")
    video_clip = VideoFileClip(video_path)
    audio_clip = AudioFileClip(audio_path)

    # --- LOGIC FOR 7-8 SECONDS ---
    target_duration = 7.5  # Hum 7.5 seconds fix karte hain (safe zone)
    
    # Agar video chhota hai toh error (usually Pixabay videos are >10s)
    if video_clip.duration < 7:
         print("Warning: Source video is short, using full length.")
         target_duration = video_clip.duration
    
    # Cut Video
    final_video = video_clip.subclip(0, target_duration)
    
    # Cut/Loop Audio
    if audio_clip.duration < target_duration:
        from moviepy.audio.fx.all import audio_loop
        final_audio = audio_loop(audio_clip, duration=target_duration)
    else:
        final_audio = audio_clip.subclip(0, target_duration)

    final_clip = final_video.set_audio(final_audio)
    
    output_filename = "final_output.mp4"
    # Preset ultrafast aur threads badhane se GitHub runner par fast hoga
    final_clip.write_videofile(output_filename, codec="libx264", audio_codec="aac", threads=4, preset='ultrafast')
    
    return output_filename

def upload_to_catbox(file_path):
    print("Uploading to Catbox...")
    url = "https://catbox.moe/user/api.php"
    with open(file_path, "rb") as f:
        payload = {'reqtype': 'fileupload'}
        files = {'fileToUpload': f}
        response = requests.post(url, data=payload, files=files)
    return response.text

def send_notifications(video_url):
    message = f"🌿 Daily Nature Dose: {video_url}"
    
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      json={"chat_id": TELEGRAM_CHAT_ID, "text": message})

    if WEBHOOK_URL:
        requests.post(WEBHOOK_URL, json={"content": message})

if __name__ == "__main__":
    try:
        v_path = get_nature_video()
        a_path = get_nature_audio()
        final_video = process_media(v_path, a_path)
        catbox_url = upload_to_catbox(final_video)
        print(f"Success! URL: {catbox_url}")
        send_notifications(catbox_url)
    except Exception as e:
        print(f"Error: {e}")
        exit(1)
