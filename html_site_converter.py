import os
import urllib.request
import re
import ssl
from bs4 import BeautifulSoup
from readability import Document
from markdownify import markdownify as md
from utils import generate_frontmatter, process_images

def fetch_html(url):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, context=ctx) as response:
            content = response.read()
            # This site uses Shift_JIS
            return content.decode('shift_jis', errors='replace')
    except Exception as e:
        print(f"Failed to fetch {url}: {e}")
        return None

def convert_html_site(base_url, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print(f"Fetching homepage to discover links: {base_url}")
    html = fetch_html(base_url)
    if not html:
        return
        
    soup = BeautifulSoup(html, 'html.parser')
    links = set()
    for a in soup.find_all('a', href=True):
        href = a['href']
        # Extract local html files like ./category1/entry2.html
        if href.startswith('./') and href.endswith('.html') and 'entry' in href:
            links.add(href[2:]) # Remove './'
            
    print(f"Found {len(links)} unique entry links. Starting conversion...")
    
    total_downloaded = 0
    for link in links:
        url = base_url + link
        print(f"Processing: {url}")
        
        page_html = fetch_html(url)
        if not page_html:
            continue
            
        try:
            # readability to extract main content
            doc = Document(page_html)
            title = doc.title()
            # Clean up title (remove site name if appended)
            title = title.split('—')[0].strip()
            title = title.replace('&#8211;', '-').replace('&#8212;', '-')
            
            summary_html = doc.summary()
            
            # Convert HTML to Markdown
            md_body = md(summary_html, heading_style="ATX")
            
            # Process images (download and replace links)
            md_body = process_images(md_body, url, output_dir)
            
            tags = ["html_site", "blog"]
            frontmatter = generate_frontmatter(title, url, tags)
            
            # Safe filename
            safe_title = re.sub(r'[\\/*?:"<>|]', "", title).strip()[:80]
            if not safe_title:
                safe_title = "Untitled"
                
            filename = f"{safe_title}.md"
            path = os.path.join(output_dir, filename)
            
            with open(path, "w", encoding="utf-8") as f:
                f.write(frontmatter + md_body)
                
            total_downloaded += 1
        except Exception as e:
            print(f"Error processing {url}: {e}")

    print(f"\nFinished downloading {total_downloaded} posts to {output_dir}")

if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "https://xn--mnqu5jib741oy19b.xyz/"
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "/Users/masashi/Documents/Obsidian Vault/資料/Web_Archives/awa_kodaisi_xyz"
    # Ensure trailing slash
    if not url.endswith('/'):
        url += '/'
    convert_html_site(url, out_dir)
