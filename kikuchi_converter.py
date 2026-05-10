import os
import re
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
from readability import Document
from markdownify import markdownify as md
from utils import generate_frontmatter, process_images

def fetch_raw_html(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.read()
    except Exception as e:
        print(f"Failed to fetch {url}: {e}")
        return None

def convert_url(start_url, output_dir, follow_links=False, base_domain="www.kikuchi2.com"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    to_visit = {start_url}
    visited = set()
    total_converted = 0

    while to_visit:
        current_url = to_visit.pop()
        if current_url in visited:
            continue
        
        print(f"Processing: {current_url}")
        visited.add(current_url)

        raw_html = fetch_raw_html(current_url)
        if not raw_html:
            continue

        try:
            # Decode HTML
            try:
                html = raw_html.decode('shift_jis', errors='replace')
            except:
                html = raw_html.decode('utf-8', errors='replace')

            # Extract main content
            doc = Document(html)
            title = doc.title()
            summary_html = doc.summary()

            # Convert to Markdown
            md_body = md(summary_html, heading_style="ATX")
            md_body = process_images(md_body, current_url, output_dir)

            tags = ["kikuchi2", "history"]
            frontmatter = generate_frontmatter(title, current_url, tags)

            # File name
            title_clean = title.split('_')[0].split(' - ')[0].split('｜')[0].strip()
            safe_title = re.sub(r'[\\/*?:"<>|]', "", title_clean).strip()[:80]
            if not safe_title or safe_title == "Untitled":
                filename = os.path.basename(urllib.parse.urlparse(current_url).path)
                if not filename:
                    filename = "index"
                safe_title = os.path.splitext(filename)[0]
            
            filename = f"{safe_title}.md"
            path = os.path.join(output_dir, filename)

            with open(path, "w", encoding="utf-8") as f:
                f.write(frontmatter + md_body)
            
            print(f"Saved: {path}")
            total_converted += 1

            # Follow links if requested
            if follow_links:
                soup = BeautifulSoup(html, 'html.parser')
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    full_url = urllib.parse.urljoin(current_url, href)
                    full_url = full_url.split('#')[0]
                    
                    parsed = urllib.parse.urlparse(full_url)
                    if parsed.netloc == base_domain:
                        if parsed.path.endswith(('.htm', '.html', '/')) or not os.path.splitext(parsed.path)[1]:
                            if full_url not in visited:
                                to_visit.add(full_url)

        except Exception as e:
            print(f"Error processing {current_url}: {e}")

    return total_converted

if __name__ == "__main__":
    out_dir = "/Users/masashi/Documents/Obsidian Vault/資料/Web_Archives/kikuchi2"
    
    # Task 1: jinno.html (Single page)
    convert_url("http://www.kikuchi2.com/chusei/rek/jinno.html", out_dir, follow_links=False)
    
    # Task 2: rikkoku.html (Follow links)
    convert_url("http://www.kikuchi2.com/sheet/rikkoku.html", out_dir, follow_links=True)

    print("Kikuchi2 conversion complete.")
