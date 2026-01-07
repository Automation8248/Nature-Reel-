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
    # Random page to get variety
    page = random.randint(1, 20)
    url = f"https://pixabay.com/api/videos/?key={PIXABAY_KEY}&q=nature&per_page=10&page={page}"
    response = requests.get(url).json()
    hits = response.get('hits', [])
    
    selected_video = None
    # Filter for unique video
    for video in hits:
        if str(video['id']) not in used_ids:
            selected_video = video
            break
            
    if not selected_video:
        selected_video = random.choice(hits)

    save_history(selected_video['id'])
    
    # Tags fetch karna bohot zaroori hai
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
    print("Processing Media (Crop 9:16 & Trim)...")
    video_clip = VideoFileClip(video_path)
    audio_clip = AudioFileClip(audio_path)

    # 1. Duration Logic (7.5 Seconds)
    target_duration = 7.5
    if video_clip.duration < 7:
         target_duration = video_clip.duration
    
    # 2. 9:16 Vertical Crop Logic
    target_ratio = 9/16
    current_ratio = video_clip.w / video_clip.h

    if current_ratio > target_ratio:
        # Calculate new width to keep height same
        new_width = int(video_clip.h * target_ratio)
        center_x = video_clip.w / 2
        
        video_clip = video_clip.crop(
            x1=center_x - (new_width / 2),
            y1=0,
            width=new_width,
            height=video_clip.h
        )
    
    # Resize to generic Shorts resolution (720x1280 is safer/faster than 1080p)
    video_clip = video_clip.resize(height=1280)
    
    # Final Trim
    final_video = video_clip.subclip(0, target_duration)
    
    # Audio Trim/Loop
    if audio_clip.duration < target_duration:
        from moviepy.audio.fx.all import audio_loop
        final_audio = audio_loop(audio_clip, duration=target_duration)
    else:
        final_audio = audio_clip.subclip(0, target_duration)

    final_clip = final_video.set_audio(final_audio)
    
    output_filename = "final_output.mp4"
    # Write file
    final_clip.write_videofile(output_filename, codec="libx264", audio_codec="aac", threads=4, preset='ultrafast')
    
    return output_filename

def generate_full_caption(tags_string):
    """Generates Title + Strict Nature Hashtags"""
    
    # 1. Parse Tags from Pixabay
    raw_tags = [t.strip() for t in tags_string.split(',')]
    main_subject = raw_tags[0].title() if raw_tags else "Nature"
    
    # 2. Create Title
    titles = [
        f"Relaxing {main_subject} Moments 🌿",
        f"Pure {main_subject} Vibes ✨",
        f"Nature's Beauty: {main_subject} 🌍",
        f"Serene {main_subject} View 🌧️",
        f"Deep {main_subject} Peace 🍃"
    ]
    title_text = random.choice(titles)

    # 3. STRICT Nature Hashtags List (No generic 'viral' tags)
    nature_keywords = [
        "#nature", "#naturelovers", "#wildlife", "#forest", "#mountains", 
        "#ocean", "#rain", "#sky", "#flowers", "#trees", 
        "#landscape", "#earth", "#river", "#sunrise", "#sunset", 
        "#animals", "#wilderness", "#scenery", "#botany", "#green",
        "#waterfall", "#jungle", "#outdoors", "#natural", "#bio"
    ]
    
    # Convert Pixabay tags to hashtags if they are safe
    video_specific_hashtags = []
    for t in raw_tags:
        clean_tag = "".join(filter(str.isalnum, t)) # Remove symbols
        if clean_tag:
            video_specific_hashtags.append(f"#{clean_tag}")
            
    # Combine lists (Prioritize video specific, then fill with general nature)
    all_pool = list(set(video_specific_hashtags + nature_keywords))
    
    # Pick 8 random tags
    if len(all_pool) > 8:
        final_tags = random.sample(all_pool, 8)
    else:
        final_tags = all_pool
        
    hashtag_string = " ".join(final_tags)
    
    # Combine Title and Hashtags
    full_caption = f"{title_text}\n\n{hashtag_string}"
    return full_caption

def send_file_notifications(file_path, caption_text):
    print("Uploading Video...")
    print(f"--- CAPTION PREVIEW ---\n{caption_text}\n-----------------------")

    # 1. Telegram Upload
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        print("Sending to Telegram...")
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendVideo"
        
        # 'data' parameter contains the caption. 'files' contains the video.
        with open(file_path, 'rb') as f:
            files = {'video': ('nature_video.mp4', f, 'video/mp4')}
            payload = {
                'chat_id': TELEGRAM_CHAT_ID,
                'caption': caption_text,
                'parse_mode': 'HTML' # Optional: Allows bolding if needed
            }
            try:
                r = requests.post(url, files=files, data=payload)
                print(f"Telegram Response: {r.status_code}")
            except Exception as e:
                print(f"Telegram Error: {e}")

    # 2. Webhook Upload
    if WEBHOOK_URL:
        print("Sending to Webhook...")
        with open(file_path, 'rb') as f:
            files = {'file': ('nature_video.mp4', f, 'video/mp4')}
            # Send caption in multiple fields to support different webhook types
            payload = {
                'content': caption_text,  # For Discord/General
                'caption': caption_text,  # For Custom
                'message': caption_text   # For Custom
            }
            try:
                requests.post(WEBHOOK_URL, files=files, data=payload)
            except Exception as e:
                print(f"Webhook Error: {e}")

if __name__ == "__main__":
    try:
        # Step 1: Get Content
        v_path, v_tags = get_nature_video()
        a_path = get_nature_audio()
        
        # Step 2: Edit Video
        final_video = process_media(v_path, a_path)
        
        # Step 3: Generate Caption
        full_caption = generate_full_caption(v_tags)
        
        # Step 4: Send
        send_file_notifications(final_video, full_caption)
        
        print("Workflow Completed Successfully!")
    except Exception as e:
        print(f"Critical Error: {e}")
        exit(1)
