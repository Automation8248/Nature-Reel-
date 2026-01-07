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
    
    # Tags fetch karna zaroori hai caption ke liye
    tags = selected_video.get('tags', 'nature')
    
    download_url = selected_video['videos']['large']['url']
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
    
    a_content = requests.get(download_url).content
    with open("input_audio.mp3", "wb") as f:
        f.write(a_content)
    return "input_audio.mp3"

def process_media(video_path, audio_path):
    print("Processing: 9:16 Crop & 7.5s Duration...")
    video_clip = VideoFileClip(video_path)
    audio_clip = AudioFileClip(audio_path)

    # Duration Logic
    target_duration = 7.5
    if video_clip.duration < 7:
         target_duration = video_clip.duration
    
    # 9:16 Vertical Crop Logic
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

def generate_nature_caption(tags_string):
    """Generates Title and STRICT Nature Hashtags"""
    
    # 1. Title Creation
    raw_tags = [t.strip() for t in tags_string.split(',')]
    main_subject = raw_tags[0].title() if raw_tags else "Nature"
    
    titles = [
        f"Relaxing {main_subject} Moments 🌿",
        f"Pure {main_subject} Vibes ✨",
        f"Discovering {main_subject} 🍃",
        f"Nature's Beauty: {main_subject} 🌍",
        f"Serene {main_subject} View 🌧️"
    ]
    selected_title = random.choice(titles)

    # 2. STRICT Nature Hashtags Only
    # Humne saare 'viral', 'shorts' hata diye hain.
    strict_nature_hashtags = [
        "#nature", "#wildlife", "#forest", "#mountains", "#ocean", 
        "#rain", "#sky", "#flowers", "#trees", "#landscape", 
        "#earth", "#planet", "#river", "#sunrise", "#sunset", 
        "#animals", "#wilderness", "#scenery", "#botany", "#green"
    ]
    
    # Video ke specific tags ko bhi hashtag banao
    video_specific_hashtags = [f"#{t.replace(' ', '')}" for t in raw_tags if t.replace(' ', '').isalpha()]
    
    # Dono lists ko combine karo
    all_nature_tags = list(set(video_specific_hashtags + strict_nature_hashtags))
    
    # Sirf 8 tags pick karo
    final_tags = random.sample(all_nature_tags, min(8, len(all_nature_tags)))
    
    # 3. Final Caption String Join
    # Format: Title + Newlines + Hashtags
    caption_text = f"{selected_title}\n\n{' '.join(final_tags)}"
    
    return caption_text

def send_file_notifications(file_path, caption_text):
    print("Uploading Video File...")
    print(f"Caption being sent:\n{caption_text}") # Log mein check karne ke liye

    # 1. Telegram
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendVideo"
        with open(file_path, 'rb') as video_file:
            # Note: 'caption' parameter is crucial here
            files = {'video': video_file}
            data = {'chat_id': TELEGRAM_CHAT_ID, 'caption': caption_text}
            requests.post(url, files=files, data=data)

    # 2. Webhook
    if WEBHOOK_URL:
        with open(file_path, 'rb') as video_file:
            files = {'file': ('video.mp4', video_file, 'video/mp4')}
            # Webhooks aksar 'content', 'caption', ya 'message' field dekhte hain
            data = {
                'content': caption_text,  # Discord/General
                'caption': caption_text,  # Custom
                'message': caption_text   # Custom
            }
            try:
                requests.post(WEBHOOK_URL, files=files, data=data)
            except Exception as e:
                print(f"Webhook Error: {e}")

if __name__ == "__main__":
    try:
        v_path, v_tags = get_nature_video()
        a_path = get_nature_audio()
        
        final_video = process_media(v_path, a_path)
        
        # New Caption Logic
        full_caption = generate_nature_caption(v_tags)
        
        send_file_notifications(final_video, full_caption)
        
        print("Workflow Completed Successfully!")
    except Exception as e:
        print(f"Error: {e}")
        exit(1)
