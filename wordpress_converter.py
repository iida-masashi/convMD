import os
import time
import urllib.request
import json
import re
from utils import process_images
from markdownify import markdownify as md

def fetch_json(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode('utf-8'))

def convert_wordpress(base_url, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    # Remove trailing slash and append API path
    base_url = base_url.rstrip('/')
    api_url_base = f"{base_url}/wp-json/wp/v2/posts"
    
    print(f"Fetching posts from WordPress API...")
    
    page = 1
    per_page = 20
    total_downloaded = 0
    
    while True:
        url = f"{api_url_base}?page={page}&per_page={per_page}"
        print(f"Fetching page {page}...")
        try:
            posts = fetch_json(url)
        except urllib.error.HTTPError as e:
            if e.code == 400:
                # Page out of range
                break
            print(f"HTTP Error: {e.code}")
            break
        except Exception as e:
            print(f"Failed to fetch: {e}")
            break
            
        if not posts:
            break
            
        for post in posts:
            # Decode HTML entities in title
            title = post.get('title', {}).get('rendered', 'Untitled')
            title = title.replace('&#8211;', '-').replace('&#8212;', '-').replace('&amp;', '&').replace('&#038;', '&')
            
            content_html = post.get('content', {}).get('rendered', '')
            post_url = post.get('link', '')
            date_str = post.get('date', '')
            
            # Convert HTML to Markdown
            md_body = md(content_html, heading_style="ATX")
            
            # Process images (download and replace links)
            md_body = process_images(md_body, post_url, output_dir)
            
            # Generate Frontmatter manually as the utils one doesn't take date as param easily
            tags_str = "wordpress, blog"
            frontmatter = f"---\ntitle: \"{title}\"\nsource: \"{post_url}\"\ndate: {date_str}\ntags: [{tags_str}]\n---\n\n"
            
            # Safe filename
            safe_title = re.sub(r'[\\/*?:"<>|]', "", title).strip()[:80]
            if not safe_title:
                safe_title = f"post_{post.get('id')}"
            
            date_prefix = date_str.split('T')[0]
            filename = f"{date_prefix}_{safe_title}.md"
            path = os.path.join(output_dir, filename)
            
            with open(path, "w", encoding="utf-8") as f:
                f.write(frontmatter + md_body)
                
            total_downloaded += 1
            
        page += 1
        time.sleep(1) # Be nice to the server
        
    print(f"\nFinished downloading {total_downloaded} posts to {output_dir}")

if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "https://kohun-jinjya.blog/"
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "/Users/masashi/Documents/Obsidian Vault/資料/Web_Archives/kohun-jinjya_blog"
    convert_wordpress(url, out_dir)
