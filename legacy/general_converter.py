import os
import re
import urllib.request
from readability import Document
from markdownify import markdownify as md
from utils import generate_frontmatter, process_images

import urllib.parse

def fetch_url(url):
    # 日本語URL対策: 一度アンクオートしてからエンコードし直す（二重エンコード防止）
    parsed = urllib.parse.urlparse(url)
    unquoted_path = urllib.parse.unquote(parsed.path)
    encoded_path = urllib.parse.quote(unquoted_path)
    encoded_url = parsed._replace(path=encoded_path).geturl()

    req = urllib.request.Request(encoded_url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        charset = response.headers.get_content_charset() or 'utf-8'
        return response.read().decode(charset, errors='replace')

def convert_to_md(url, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    print(f"Processing {url} with Readability engine...")
    try:
        html = fetch_url(url)
    except Exception as e:
        print(f"Failed to fetch {url}: {e}")
        return None
    
    # Readabilityで本文だけを抽出
    doc = Document(html)
    title = doc.title()
    summary_html = doc.summary()
    
    # HTMLをMarkdownに変換
    md_body = md(summary_html, heading_style="ATX")
    
    # 画像のローカルダウンロード＆リンク置換
    print("Downloading images and updating links...")
    md_body = process_images(md_body, url, output_dir)
    
    # Obsidian用Frontmatterの生成
    frontmatter = generate_frontmatter(title, url, tags=["web_clip"])
    
    safe_title = re.sub(r'[\\/*?:"<>|]', "", title).strip()[:100]
    if not safe_title:
        safe_title = "Untitled"
    filename = f"{safe_title}.md"
    path = os.path.join(output_dir, filename)
    
    with open(path, "w", encoding="utf-8") as f:
        f.write(frontmatter + md_body)
    
    print(f"Saved to {path}")
    return path
