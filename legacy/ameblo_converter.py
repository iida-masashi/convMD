import os
import re
import urllib.request
from bs4 import BeautifulSoup
from readability import Document
from markdownify import markdownify as md
from utils import generate_frontmatter, process_images
import time

def fetch_html(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"Failed to fetch {url}: {e}")
        return None

def convert_ameblo(base_id, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print(f"Starting Ameblo crawl for: {base_id}")
    
    # 1. 記事URLを収集
    article_urls = set()
    page = 1
    
    while True:
        list_url = f"https://ameblo.jp/{base_id}/entrylist-{page}.html"
        print(f"Fetching list page: {list_url}")
        
        html = fetch_html(list_url)
        if not html:
            break
            
        soup = BeautifulSoup(html, 'html.parser')
        
        # entry-*.html へのリンクを探す
        found_on_page = 0
        for a in soup.find_all('a', href=True):
            href = a['href']
            # Amebloの個別記事URLパターン
            if f"/{base_id}/entry-" in href and href.endswith('.html'):
                if not href.startswith('http'):
                    href = "https://ameblo.jp" + href
                
                # パラメータを除去
                clean_url = href.split('?')[0]
                
                if clean_url not in article_urls:
                    article_urls.add(clean_url)
                    found_on_page += 1
        
        print(f"Found {found_on_page} articles on page {page}.")
        
        # 記事が見つからなくなったら終了（全ページ取得完了）
        if found_on_page == 0:
            # ページャー自体が存在しないかチェック
            if "次のページ" not in html and "pagingNext" not in html:
                break
        
        page += 1
        time.sleep(1) # サーバ負荷軽減
        
    print(f"\nTotal unique articles found: {len(article_urls)}")
    print("Starting conversion...")
    
    # 2. 記事をダウンロードして変換
    total_converted = 0
    for url in article_urls:
        print(f"Processing: {url}")
        html = fetch_html(url)
        if not html:
            continue
            
        try:
            # Ameblo独自の本文エリア指定があればそれを使うが、まずはreadabilityで試す
            doc = Document(html)
            title = doc.title()
            
            # Amebloのタイトルは「記事タイトル | ブログタイトル」になりがちなので整形
            title = title.split(' | ')[0].strip()
            
            summary_html = doc.summary()
            
            # Markdown化
            md_body = md(summary_html, heading_style="ATX")
            
            # 日付の抽出 (Ameblo HTMLから)
            soup = BeautifulSoup(html, 'html.parser')
            date_str = ""
            time_elem = soup.find('time')
            if time_elem and time_elem.has_attr('datetime'):
                date_str = time_elem['datetime']
            
            # 画像処理
            md_body = process_images(md_body, url, output_dir)
            
            # Frontmatter
            frontmatter = f"---\ntitle: \"{title}\"\nsource: \"{url}\"\n"
            if date_str:
                frontmatter += f"date: {date_str}\n"
            frontmatter += f"tags: [ameblo, {base_id}]\n---\n\n"
            
            # ファイル名
            safe_title = re.sub(r'[\\/*?:"<>|]', "", title).strip()[:80]
            if not safe_title:
                safe_title = "Untitled"
            
            # 日付プレフィックス
            prefix = ""
            if date_str:
                prefix = date_str.split('T')[0] + "_"
            elif date_str == "":
                prefix = ""
                
            filename = f"{prefix}{safe_title}.md"
            path = os.path.join(output_dir, filename)
            
            with open(path, "w", encoding="utf-8") as f:
                f.write(frontmatter + md_body)
                
            total_converted += 1
            time.sleep(0.5)
            
        except Exception as e:
            print(f"Error processing {url}: {e}")

    print(f"\nFinished! Converted {total_converted} articles to {output_dir}")

if __name__ == "__main__":
    import sys
    base_id = sys.argv[1] if len(sys.argv) > 1 else "marine816"
    out_dir = sys.argv[2] if len(sys.argv) > 2 else f"/Users/masashi/Documents/Obsidian Vault/資料/Web_Archives/ameblo_{base_id}"
    convert_ameblo(base_id, out_dir)
