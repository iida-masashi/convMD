import os
import re
import json
import urllib.request
from youtube_transcript_api import YouTubeTranscriptApi
from utils import generate_frontmatter

def get_video_id(url):
    # 動画IDを抽出する正規表現
    match = re.search(r'(?:v=|/)([0-9A-Za-z_-]{11}).*', url)
    if match:
        return match.group(1)
    return None

def get_video_title(video_id):
    try:
        url = f"https://www.youtube.com/oembed?url=http://www.youtube.com/watch?v={video_id}&format=json"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data.get('title', f"YouTube_Video_{video_id}")
    except:
        return f"YouTube_Video_{video_id}"

def format_time(seconds):
    mins, secs = divmod(int(seconds), 60)
    hours, mins = divmod(mins, 60)
    if hours > 0:
        return f"{hours}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"

def convert_youtube(url, output_dir):
    video_id = get_video_id(url)
    if not video_id:
        print("Could not extract YouTube Video ID.")
        return None

    print(f"Fetching transcript for video ID: {video_id}...")
    
    try:
        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)
        try:
            transcript = transcript_list.find_transcript(['ja', 'en']).fetch()
        except:
            for t in transcript_list:
                transcript = t.fetch()
                break
    except Exception as e:
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
        except Exception as e2:
            print(f"Failed to fetch transcript: {e2}")
            return None

    title = get_video_title(video_id)
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    # Obsidian用Frontmatter
    frontmatter = generate_frontmatter(title, url, tags=["youtube", "transcript"])
    
    # タイムスタンプ付きのMarkdown文字列作成
    thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
    md_body = f"![Thumbnail]({thumbnail_url})\n\n## 動画情報\n- **タイトル**: {title}\n- **URL**: {url}\n\n## 文字起こし\n\n"
    
    for entry in transcript:
        try:
            start = entry['start']
            text = entry['text']
        except TypeError:
            start = entry.start
            text = entry.text
            
        start_time = format_time(start)
        text = text.replace('\n', ' ')
        md_body += f"**[{start_time}]** {text}\n\n"
        
    safe_title = re.sub(r'[\\/*?:"<>|]', "", title).strip()[:100]
    filename = f"{safe_title}.md"
    path = os.path.join(output_dir, filename)
    
    with open(path, "w", encoding="utf-8") as f:
        f.write(frontmatter + md_body)
        
    print(f"Saved YouTube transcript to {path}")
    return path
