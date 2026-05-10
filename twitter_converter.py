import json
import os
import urllib.request
import re
from datetime import datetime

def fetch_twitter_timeline(screen_name):
    url = f"https://syndication.twitter.com/srv/timeline-profile/screen-name/{screen_name}"
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8'
    })
    
    print(f"Fetching timeline for @{screen_name}...")
    try:
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8')
    except Exception as e:
        print(f"Failed to fetch timeline: {e}")
        return None

    # Extract __NEXT_DATA__ JSON from HTML
    match = re.search(r'id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if not match:
        print("Could not find timeline data in the response.")
        return None
    
    json_data = match.group(1)
    try:
        data = json.loads(json_data)
        entries = data['props']['pageProps']['timeline']['entries']
        return entries
    except Exception as e:
        print(f"Error parsing JSON data: {e}")
        return None

def parse_and_save_tweets(screen_name, entries, output_dir="note_posts"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    tweets = []
    
    for entry in entries:
        if entry['type'] == 'tweet':
            tweet_data = entry['content']['tweet']
            
            tweet_id = tweet_data.get('id_str')
            created_at = tweet_data.get('created_at') # e.g., "Sat Sep 14 01:16:40 +0000 2024"
            text = tweet_data.get('text', '')
            
            # Format Date
            try:
                date_obj = datetime.strptime(created_at, "%a %b %d %H:%M:%S %z %Y")
                date_str = date_obj.strftime("%Y-%m-%d %H:%M:%S")
                date_short = date_obj.strftime("%Y-%m-%d")
            except:
                date_str = created_at
                date_short = "unknown_date"
            
            # Extract Media
            media_urls = []
            entities = tweet_data.get('entities', {})
            if 'media' in entities:
                for m in entities['media']:
                    media_url = m.get('media_url_https')
                    if media_url:
                        media_urls.append(media_url)
                        # Remove the t.co URL from text to keep it clean
                        url_tco = m.get('url', '')
                        if url_tco:
                            text = text.replace(url_tco, '').strip()

            tweets.append({
                'id': tweet_id,
                'date': date_str,
                'short_date': date_short,
                'text': text,
                'media': media_urls
            })
            
    if not tweets:
        print("No tweets found.")
        return

    print(f"Found {len(tweets)} tweets. Converting to Markdown...")
    
    md_filename = f"{screen_name}_tweets.md"
    md_path = os.path.join(output_dir, md_filename)
    
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# @{screen_name} の投稿まとめ\n\n")
        f.write(f"取得日: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("---\n\n")
        
        for t in tweets:
            f.write(f"### {t['date']} (ID: {t['id']})\n\n")
            f.write(f"{t['text']}\n\n")
            
            for m in t['media']:
                f.write(f"![image]({m})\n\n")
                
            f.write(f"[Twitterで見る](https://x.com/{screen_name}/status/{t['id']})\n\n")
            f.write("---\n\n")
            
    print(f"Saved {len(tweets)} tweets to {md_path}")

if __name__ == "__main__":
    import sys
    screen_name = sys.argv[1] if len(sys.argv) > 1 else "kamiyamafudoki"
    entries = fetch_twitter_timeline(screen_name)
    if entries:
        parse_and_save_tweets(screen_name, entries)
