import os
import urllib.request
from html.parser import HTMLParser

class KojikiHTMLToMarkdown(HTMLParser):
    def __init__(self, base_url):
        super().__init__()
        self.markdown = ""
        self.in_a = False
        self.a_href = ""
        self.list_stack = []
        self.base_url = base_url
        self.ignore_tags = ["script", "style", "head", "title", "meta"]
        self.in_ignored = False

    def handle_starttag(self, tag, attrs):
        if tag in self.ignore_tags:
            self.in_ignored = True
            return

        if self.in_ignored:
            return

        attrs_dict = dict(attrs)
        
        if tag in ["b", "strong"]:
            self.markdown += "**"
        elif tag == "br":
            self.markdown += "\n"
        elif tag in ["p", "div", "tr"]:
            if not self.markdown.endswith("\n\n"):
                self.markdown += "\n\n"
        elif tag == "a":
            self.in_a = True
            self.a_href = attrs_dict.get("href", "")
            if self.a_href and not self.a_href.startswith("http"):
                self.a_href = urllib.parse.urljoin(self.base_url, self.a_href)
            self.markdown += "["
        elif tag == "img":
            src = attrs_dict.get("src", "")
            if src and not src.startswith("http"):
                src = urllib.parse.urljoin(self.base_url, src)
            alt = attrs_dict.get("alt", "image")
            self.markdown += f"![{alt}]({src})"
        elif tag in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            try:
                level = int(tag[1])
            except:
                level = 1
            self.markdown += "\n\n" + ("#" * level) + " "
        elif tag == "font":
            size = attrs_dict.get("size", "")
            if "+1" in size or "+2" in size or "+3" in size:
                self.markdown += "\n## "

    def handle_endtag(self, tag):
        if tag in self.ignore_tags:
            self.in_ignored = False
            return

        if self.in_ignored:
            return

        if tag in ["b", "strong"]:
            self.markdown += "**"
        elif tag == "a":
            self.in_a = False
            self.markdown += f"]({self.a_href})"
        elif tag in ["p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "tr"]:
            if not self.markdown.endswith("\n\n"):
                self.markdown += "\n\n"

    def handle_data(self, data):
        if not self.in_ignored:
            text = data.replace('\r', '').replace('\n', '')
            import re
            text = re.sub(r'\s+', ' ', text)
            if text.strip():
                self.markdown += text

def convert_site():
    output_dir = "kojiki_md"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    base_url = "http://park17.wakwak.com/~happyend/kojiki/awa/"
    
    # We found awa_01.html through awa_11.html
    for i in range(1, 12):
        filename = f"awa_{i:02d}.html"
        url = base_url + filename
        print(f"Downloading {url}...")
        
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        try:
            with urllib.request.urlopen(req) as response:
                # The site uses Shift_JIS encoding
                html_content = response.read().decode('shift_jis', errors='replace')
                
                parser = KojikiHTMLToMarkdown(base_url)
                parser.feed(html_content)
                
                md_content = parser.markdown
                # Clean up multiple newlines
                import re
                md_content = re.sub(r'\n{3,}', '\n\n', md_content)
                
                out_filename = f"awa_{i:02d}.md"
                out_path = os.path.join(output_dir, out_filename)
                
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(md_content)
                print(f"Saved to {out_path}")
        except Exception as e:
            print(f"Failed to process {url}: {e}")

if __name__ == "__main__":
    import urllib.parse
    convert_site()
