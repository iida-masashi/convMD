import sys
import os
from urllib.parse import urlparse

# Add current directory to path so we can import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import note_converter
import twitter_converter
import kojiki_converter
import general_converter
import office_converter
import youtube_converter

# デフォルトの保存先をObsidian Vaultに設定
OBSIDIAN_VAULT_DIR = "/Users/masashi/Documents/Obsidian Vault/資料/Web_Archives"

def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <URL_or_Local_File>")
        sys.exit(1)

    target = sys.argv[1]

    # Check if it's a local file first
    if os.path.isfile(target):
        print(f"Detected local file: {target}")
        office_extensions = ['.pptx', '.xlsx', '.docx', '.pdf', '.html', '.csv', '.json', '.xml']
        _, ext = os.path.splitext(target)
        if ext.lower() in office_extensions:
            office_converter.convert_office_file(target, output_dir=OBSIDIAN_VAULT_DIR)
        else:
            print(f"Extension {ext} might not be fully supported by MarkItDown, but we will try anyway.")
            office_converter.convert_office_file(target, output_dir=OBSIDIAN_VAULT_DIR)
        return

    # If not a local file, treat as URL
    parsed_url = urlparse(target)
    domain = parsed_url.netloc

    print(f"Analyzing URL: {target}")

    if "note.com" in domain:
        # Check if it's a profile or a single post
        parts = parsed_url.path.strip("/").split("/")
        if len(parts) == 1:
            print("Detected note.com creator profile. Fetching all notes...")
            note_converter.convert_note_com(parts[0], output_dir=os.path.join(OBSIDIAN_VAULT_DIR, "note_posts"))
        else:
            print("Detected note.com single post. Converting with Readability...")
            general_converter.convert_to_md(target, output_dir=OBSIDIAN_VAULT_DIR)

    elif "x.com" in domain or "twitter.com" in domain:
        parts = parsed_url.path.strip("/").split("/")
        if len(parts) >= 1:
            screen_name = parts[0]
            print(f"Detected X.com account: @{screen_name}. Fetching recent tweets...")
            entries = twitter_converter.fetch_twitter_timeline(screen_name)
            if entries:
                twitter_converter.parse_and_save_tweets(screen_name, entries, output_dir=OBSIDIAN_VAULT_DIR)

    elif "park17.wakwak.com" in domain and "kojiki" in target:
        print("Detected Kojiki site. Starting specialized crawl...")
        # Note: Kojiki converter is currently hardcoded for its directory structure.
        kojiki_converter.convert_site()

    elif "youtube.com" in domain or "youtu.be" in domain:
        print("Detected YouTube video. Extracting transcript...")
        youtube_converter.convert_youtube(target, output_dir=OBSIDIAN_VAULT_DIR)

    else:
        print("Detected general website. Extracting main content with Readability...")
        general_converter.convert_to_md(target, output_dir=OBSIDIAN_VAULT_DIR)

if __name__ == "__main__":
    main()
