# -*- coding: utf-8 -*-
import os
import glob
import re

base_dir = "/Users/masashi/Documents/Obsidian Vault"
list_file = "/Users/masashi/Documents/Obsidian Vault/管理用索引/未分類ブログ記事アーカイブ.md"

if not os.path.exists(list_file):
    print("List file not found.")
    exit()

with open(list_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Extract links format: [[path/to/file.md|alias]]
lines = content.split('\n')
files_to_process = []

for line in lines:
    if line.startswith("- "):
        item = line[2:].strip()
        match = re.search(r'\[\[(.*?)\]\]', item)
        if match:
            inner = match.group(1)
            path = inner.split('|')[0]
            files_to_process.append(path)
        else:
            files_to_process.append(item)

# Determine relevant specialized notes based on keywords
specialized_links = {
    "阿波説の概論_なぜ徳島が日本の起源とされるのか": ["阿波", "徳島", "高天原", "忌部", "神山町", "八倉比売", "大御和", "吉野川"],
    "高天原と天孫降臨_剣山に隠された神話": ["剣山", "天孫降臨", "大宜都比売", "天岩戸"],
    "邪馬台国阿波説と若杉山辰砂採掘遺跡": ["邪馬台国", "魏志倭人伝", "辰砂"],
    "神代文字の概論と研究史_徹底解説": ["神代文字", "トホカミエヒタメ"],
    "記紀神話と古代日本の建国": ["古事記", "日本書紀", "神話", "天皇", "日向三代", "大国主", "伊弉諾", "伊射奈美", "国造"],
    "古墳時代と古代国家の成り立ち": ["古墳", "氏族", "豪族", "白村江", "百済", "蘇我", "物部", "飛鳥", "持統天皇", "大化の改新"],
    "神社信仰と古墳の歴史的意義": ["神社", "一宮", "祭祀", "神階", "磐座", "神籬", "遥拝所", "縁起"],
    "東国古代史と香取海の神々": ["東国", "香取", "鹿島", "大生神社"],
    "平将門の首塚の祟り": ["平将門", "首塚"],
    "六国史と古代の正史": ["六国史", "正史"],
    "平家物語と源平盛衰記の概論": ["平家物語", "源平盛衰記", "高野本", "延慶本", "長門本"],
    "古史古伝の概要と歴史的背景": ["古史古伝"],
    "現代怪異_ネット都市伝説": ["きさらぎ駅", "八尺様", "コトリバコ", "丑の刻参り", "かごめかごめ"] # A catch-all for urban legends if needed, or specific ones.
}

# The specific urban legend notes exist, so map directly
specific_urban_legends = {
    "きさらぎ駅": "きさらぎ駅_異界への迷い込み",
    "八尺様": "八尺様_魅入られたら逃げられない怪異",
    "コトリバコ": "コトリバコ_呪いの箱",
    "丑の刻参り": "丑の刻参りと呪術の歴史",
    "かごめかごめ": "かごめかごめの隠された意味",
    "平将門": "平将門の首塚の祟り"
}


relinked_count = 0

for file_path in files_to_process:
    full_path = os.path.join(base_dir, file_path)
    
    # If the exact path doesn't exist, try fuzzy search
    target_files = []
    if os.path.exists(full_path):
        target_files.append(full_path)
    else:
        filename = os.path.basename(file_path)
        if not filename.endswith('.md'):
            if not "&" in filename:
                filename += ".md"
        search_path = os.path.join(base_dir, "**", filename)
        target_files = glob.glob(search_path, recursive=True)

    for target in target_files:
        try:
            with open(target, 'r', encoding='utf-8') as f:
                file_content = f.read()
            
            # Determine notes to add
            links_to_add = []
            
            # 1. Check specific urban legends in filename
            fname = os.path.basename(target)
            for kw, note in specific_urban_legends.items():
                if kw in fname:
                    links_to_add.append(note)
            
            # 2. Check general keywords in filename and content
            for note_name, keywords in specialized_links.items():
                if note_name in links_to_add:
                    continue
                if any(kw in fname or kw in file_content for kw in keywords):
                    links_to_add.append(note_name)
                    
            # If no matches found, default to a broad category
            if not links_to_add:
                if "神社" in fname:
                    links_to_add.append("神社信仰と古墳の歴史的意義")
                elif "kikuchi2" in target:
                    links_to_add.append("六国史と古代の正史")
                else:
                    links_to_add.append("記紀神話と古代日本の建国")
                    
            # Add links to the file
            original_content = file_content
            for note in links_to_add:
                link_str = f"[[{note}]]"
                if link_str not in file_content:
                    if "## 関連する専門ノート" in file_content:
                        file_content = file_content.replace("## 関連する専門ノート\n", f"## 関連する専門ノート\n- {link_str}\n")
                    else:
                        # Append before the related resources footer if it exists
                        parts = file_content.split("---\n> [!link] 関連リソース")
                        if len(parts) == 2:
                            file_content = parts[0].strip() + f"\n\n---\n## 関連する専門ノート\n- {link_str}\n\n---\n> [!link] 関連リソース" + parts[1]
                        else:
                            file_content = file_content.strip() + f"\n\n---\n## 関連する専門ノート\n- {link_str}\n"
            
            if file_content != original_content:
                with open(target, 'w', encoding='utf-8') as f:
                    f.write(file_content)
                relinked_count += 1
                
        except Exception as e:
            print(f"Error processing {target}: {e}")

# Delete the index file
try:
    os.remove(list_file)
    print(f"\nDeleted index file: {list_file}")
except Exception as e:
    print(f"\nFailed to delete index file: {e}")

print(f"Successfully re-linked {relinked_count} files.")
