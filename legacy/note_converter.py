import os
import re
import json
import time
import urllib.request
import urllib.parse
from datetime import datetime
from html.parser import HTMLParser

class HTMLToMarkdown(HTMLParser):
    def __init__(self):
        super().__init__()
        self.markdown = ""
        self.in_a = False
        self.a_href = ""
        self.list_stack = []
        self.in_quote = False
        self.in_caption = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag in ["b", "strong"]:
            self.markdown += "**"
        elif tag in ["i", "em"]:
            self.markdown += "*"
        elif tag == "br":
            self.markdown += "\n"
        elif tag in ["p", "div"]:
            if not self.markdown.endswith("\n\n"):
                self.markdown += "\n\n"
        elif tag == "a":
            self.in_a = True
            self.a_href = attrs_dict.get("href", "")
            self.markdown += "["
        elif tag == "img":
            src = attrs_dict.get("src", "")
            alt = attrs_dict.get("alt", "image")
            self.markdown += f"![{alt}]({src})"
        elif tag in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            try:
                level = int(tag[1])
            except:
                level = 1
            self.markdown += "\n\n" + ("#" * level) + " "
        elif tag == "ul":
            self.list_stack.append("ul")
            self.markdown += "\n"
        elif tag == "ol":
            self.list_stack.append("ol")
            self.markdown += "\n"
        elif tag == "li":
            indent = "  " * (len(self.list_stack) - 1)
            if self.list_stack and self.list_stack[-1] == "ul":
                self.markdown += f"\n{indent}- "
            else:
                self.markdown += f"\n{indent}1. "
        elif tag == "blockquote":
            self.in_quote = True
            self.markdown += "\n\n> "
        elif tag == "figcaption":
            self.in_caption = True
            self.markdown += "\n\n*"

    def handle_endtag(self, tag):
        if tag in ["b", "strong"]:
            self.markdown += "**"
        elif tag in ["i", "em"]:
            self.markdown += "*"
        elif tag == "a":
            self.in_a = False
            self.markdown += f"]({self.a_href})"
        elif tag in ["p", "div", "h1", "h2", "h3", "h4", "h5", "h6"]:
            if not self.markdown.endswith("\n\n"):
                self.markdown += "\n\n"
        elif tag in ["ul", "ol"]:
            if self.list_stack:
                self.list_stack.pop()
            self.markdown += "\n"
        elif tag == "blockquote":
            self.in_quote = False
            self.markdown += "\n\n"
        elif tag == "figcaption":
            self.in_caption = False
            self.markdown += "*\n\n"

    def handle_data(self, data):
        if self.in_quote:
            data = data.replace("\n", "\n> ")
        self.markdown += data

def clean_filename(title):
    title = re.sub(r'[\\/*?:"<>|]', "", title)
    title = title.replace(" ", "_")
    return title[:100]

def fetch_json(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode('utf-8'))

def convert_note_com(urlname, output_dir="note_posts"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    page = 1
    all_notes = []
    
    print(f"Fetching note list for {urlname}...")
    while True:
        url = f"https://note.com/api/v2/creators/{urlname}/contents?kind=note&page={page}"
        data = fetch_json(url)
        notes = data['data']['contents']
        if not notes:
            break
        all_notes.extend(notes)
        if data['data']['isLastPage']:
            break
        page += 1
        time.sleep(1) # Be nice
    
    print(f"Found {len(all_notes)} notes. Starting conversion...")
    
    for note in all_notes:
        key = note['key']
        title = note['name']
        publish_at = note['publishAt']
        
        # Get full content
        try:
            note_url = f"https://note.com/api/v3/notes/{key}"
            note_data = fetch_json(note_url)
            html_body = note_data['data']['body']
            
            # Convert
            parser = HTMLToMarkdown()
            parser.feed(html_body)
            md_body = parser.markdown
            
            # Frontmatter
            date_obj = datetime.fromisoformat(publish_at.replace('Z', '+00:00'))
            date_str = date_obj.strftime("%Y-%m-%d")
            
            frontmatter = f"---\ntitle: \"{title}\"\ndate: {publish_at}\nkey: {key}\n---\n\n"
            
            filename = f"{date_str}-{clean_filename(title)}.md"
            file_path = os.path.join(output_dir, filename)
            
            with open(file_path, "w", encoding='utf-8') as f:
                f.write(frontmatter + md_body)
            
            print(f"Converted: {filename}")
            time.sleep(0.5)
        except Exception as e:
            print(f"Error converting {key} ({title}): {e}")

if __name__ == "__main__":
    import sys
    urlname = sys.argv[1] if len(sys.argv) > 1 else "cute_hebe442"
    convert_note_com(urlname)
