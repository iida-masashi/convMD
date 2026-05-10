import os
import re
import urllib.request
from urllib.parse import urljoin, urlparse
from datetime import datetime

def generate_frontmatter(title, url, tags=None):
    if tags is None:
        tags = []
    tags_str = ", ".join(tags)
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"---\ntitle: \"{title}\"\nsource: \"{url}\"\ndate: {date_str}\ntags: [{tags_str}]\n---\n\n"

def process_images(md_content, base_url, output_dir):
    image_dir = os.path.join(output_dir, "images")
    if not os.path.exists(image_dir):
        os.makedirs(image_dir)

    # Markdownの画像リンク ![alt](url) を抽出
    img_pattern = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
    
    def replace_img(match):
        alt_text = match.group(1)
        img_url = match.group(2)
        
        # Base64画像は無視
        if img_url.startswith("data:"):
            return match.group(0)
            
        # 相対パスなら絶対パスに変換
        if not img_url.startswith("http"):
            img_url = urljoin(base_url, img_url)
            
        try:
            parsed_url = urlparse(img_url)
            filename = os.path.basename(urllib.parse.unquote(parsed_url.path))
            if not filename or '.' not in filename:
                filename = "image_" + str(hash(img_url))[1:9] + ".jpg"
            
            # ファイル名を安全に
            filename = re.sub(r'[\\/*?:"<>|]', "", filename)
            local_img_path = os.path.join(image_dir, filename)
            
            # URLエンコード（日本語ファイル名対策）
            encoded_path = urllib.parse.quote(parsed_url.path)
            safe_img_url = parsed_url._replace(path=encoded_path).geturl()
            
            # SSLエラー対策
            import ssl
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            # まだダウンロードしていなければダウンロード
            if not os.path.exists(local_img_path):
                req = urllib.request.Request(safe_img_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=10, context=ctx) as response, open(local_img_path, 'wb') as out_file:
                    out_file.write(response.read())
                    
            # リンクをローカル（相対パス）に置き換え
            return f"![{alt_text}](images/{filename})"
        except Exception as e:
            print(f"Failed to download image {img_url}: {e}")
            return match.group(0)

    new_md = img_pattern.sub(replace_img, md_content)
    return new_md
