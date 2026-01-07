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
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r") as f:
        return f.read().splitlines()

def save_history(video_id):
    with open(HISTORY_FILE, "a") as f:
        f.write(f"{str(video_id)}\n")

def get_nature_video():
    """Fetches unique nature video and its tags"""
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
        print("Warning: Repeats possible, picking random.")
        selected_video = random.choice(hits)

    save_history(selected_video['id'])
    
    # Extract Tags for caption
    tags = selected_video.get('tags', 'nature, beauty')
    
    # Download Video
    download_url = selected_video['videos']['large']['url']
    print(f"Downloading video ID: {selected_video['id']}...")
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
    
    print(f"Downloading audio: {audio_data['name']}...")
    a_content = requests.get(download_url).content
    with open("input_audio.mp3", "wb") as f:
        f.write(a_content)
    return "input_audio.mp3"

def process_media(video_path, audio_path):
    print("Processing: Converting to Shorts (9:16) & Trimming...")
    video_clip = VideoFileClip(video_path)
    audio_clip = AudioFileClip(audio_path)

    # 1. Logic for 7-8 Seconds Duration
    target_duration = 7.5
    if video_clip.duration < 7:
         target_duration = video_clip.duration
    
    # 2. Logic for YouTube Shorts (9:16 Aspect Ratio)
    # Hamein width ko cut karna hoga taaki height wahi rahe
    # Formula: New Width = Height * (9/16)
    target_ratio = 9/16
    current_ratio = video_clip.w / video_clip.h

    if current_ratio > target_ratio:
        # Landscape video hai, sides se crop karo
        new_width = int(video_clip.h * target_ratio)
        center_x = video_clip.w / 2
        # Center Crop: (x1, y1, width, height)
        video_clip = video_clip.crop(
            x1=center_x - (new_width / 2),
            y1=0,
            width=new_width,
            height=video_clip.h
        )
        print("Video cropped to 9:16 vertical format.")
    
    # Resize to standard HD Shorts size (optional but good for consistency)
    video_clip = video_clip.resize(height=1280)

    # Trim Time
    final_video = video_clip.subclip(0, target_duration)
    
    # Audio Setup
    if audio_clip.duration < target_duration:
        from moviepy.audio.fx.all import audio_loop
        final_audio = audio_loop(audio_clip, duration=target_duration)
    else:
        final_audio = audio_clip.subclip(0, target_duration)

    final_clip = final_video.set_audio(final_audio)
    
    output_filename = "final_output.mp4"
    # 'preset=ultrafast' for speed on GitHub
    final_clip.write_videofile(output_filename, codec="libx264", audio_codec="aac", threads=4, preset='ultrafast')
    
    return output_filename

def generate_caption(tags_string):
    """Generates Title and Hashtags"""
    tags = [t.strip() for t in tags_string.split(',')]
    main_tag = tags[0].title() if tags else "Nature"
    
    # Simple Title
    title = f"Peaceful {main_tag} Vibes 🌿"
    
    # Hashtags
    generic_hashtags = ["#shorts", "#nature", "#relaxing", "#peace", "#reels", "#fyp", "#viral", "#zen"]
    video_hashtags = [f"#{t.replace(' ', '')}" for t in tags]
    all_tags = list(set(video_hashtags + generic_hashtags))
    
    # Select 8
    final_tags = random.sample(all_tags, min(8, len(all_tags)))
    caption = f"{title}\n\n{' '.join(final_tags)}"
    return caption

def send_file_notifications(file_path, caption):
    print("Uploading Video File directly...")
    
    # 1. Telegram Video Upload
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        print("Sending to Telegram...")
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendVideo"
        
        # File open karke bhejna padta hai
        with open(file_path, 'rb') as video_file:
            files = {'video': video_file}
            data = {'chat_id': TELEGRAM_CHAT_ID, 'caption': caption}
            requests.post(url, files=files, data=data)

    # 2. Webhook Video Upload (Multipart)
    if WEBHOOK_URL:
        print("Sending to Webhook...")
        # Note: Webhook must support file upload (like Make.com / n8n)
        with open(file_path, 'rb') as video_file:
            # Bahut se webhook 'file' naam se data expect karte hain
            files = {'file': ('video.mp4', video_file, 'video/mp4')}
            data = {'content': caption} # Content field for text
            try:
                requests.post(WEBHOOK_URL, files=files, data=data)
            except Exception as e:
                print(f"Webhook Error: {e}")

if __name__ == "__main__":
    try:
        v_path, v_tags = get_nature_video()
        a_path = get_nature_audio()
        
        # Shorts Logic inside process_media
        final_video = process_media(v_path, a_path)
        
        # Caption Logic
        full_caption = generate_caption(v_tags)
        
        # Send File Logic
        send_file_notifications(final_video, full_caption)
        
        print("Workflow Completed Successfully!")
    except Exception as e:
        print(f"Error: {e}")
        exit(1)
