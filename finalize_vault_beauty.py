# -*- coding: utf-8 -*-
import os
import glob
import re

base_dir = "/Users/masashi/Documents/Obsidian Vault/資料/Web_Archives"
moc_file = "00_古代史研究アーカイブ_MOC"

# 1. Improve Specialized Notes with Callouts and better formatting
def beautify_specialized_notes():
    search_path = os.path.join(base_dir, "**", "*専門ノート*", "*.md")
    notes = glob.glob(search_path, recursive=True)
    
    for note_path in notes:
        with open(note_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        new_lines = []
        in_frontmatter = False
        frontmatter_done = False
        
        for line in lines:
            if line.strip() == "---" and not frontmatter_done:
                if not in_frontmatter:
                    in_frontmatter = True
                else:
                    in_frontmatter = False
                    frontmatter_done = True
                new_lines.append(line)
                continue
            
            if in_frontmatter:
                new_lines.append(line)
                continue
            
            # Convert main headers to include icons or formatting
            if line.startswith("# "):
                title = line.replace("# ", "").strip()
                new_lines.append(f"# 🎓 {title}\n")
                new_lines.append(f"> [!abstract] このノートの概要\n> このページは、古代史・ミステリー研究アーカイブにおける専門的なまとめノートです。\n\n")
                continue
            
            # Wrap key sections in callouts
            if line.startswith("## 1. ") or line.startswith("## 概要"):
                new_lines.append(f"> [!info] 基礎知識\n")
                new_lines.append(line.replace("## ", "### "))
                continue
            
            new_lines.append(line)
            
        with open(note_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
            f.write(f"\n\n---\n[[{moc_file}|🔙 研究アーカイブ目次に戻る]]\n")

# 2. Add 'Return to MOC' footer to EVERY article file
def standardize_all_articles():
    files = glob.glob(os.path.join(base_dir, "**/*.md"), recursive=True)
    
    for file_path in files:
        # Skip internal files
        if moc_file in file_path or "専門ノート" in file_path or "インデックス" in file_path:
            continue
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if f"[[{moc_file}" in content:
            continue
            
        footer = f"\n\n---\n> [!link] 関連リソース\n> - [[{moc_file}|📁 研究アーカイブ目次 (MOC)]]\n"
        
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(footer)

# 3. Create 'Thematic Indexes' for all source articles
def create_thematic_indexes():
    sources = {
        "ameblo_marine816": "Amebaブログ (marine816) 考察資料集",
        "note_kofunjidaishi": "古墳時代史 note 収集資料",
        "note_rakujin_01": "日本古代史 note 収集資料",
        "kikuchi2": "菊池氏 古典籍・歴史資料アーカイブ",
        "kamimasu_com": "神々の坐す処 (kamimasu.com) 収集資料",
        "note_kometake": "この国は誰の神話か 収集資料"
    }
    
    index_dir = os.path.join(base_dir, "99_インデックス")
    os.makedirs(index_dir, exist_ok=True)
    
    for folder, desc in sources.items():
        folder_path = os.path.join(base_dir, folder)
        if not os.path.exists(folder_path): continue
        
        idx_content = f"# {desc}\n\nこのページは、`{folder}` フォルダ内の全資料を一覧化したインデックスです。\n\n"
        
        md_files = glob.glob(os.path.join(folder_path, "**/*.md"), recursive=True)
        
        groups = {}
        for f in md_files:
            rel = os.path.relpath(f, folder_path)
            parts = rel.split(os.sep)
            group_name = parts[0] if len(parts) > 1 else "未分類"
            if group_name not in groups: groups[group_name] = []
            groups[group_name].append(os.path.basename(f))
            
        for group, filenames in sorted(groups.items()):
            idx_content += f"## 📁 {group}\n"
            for fname in sorted(filenames):
                idx_content += f"- [[{fname.replace('.md', '')}]]\n"
            idx_content += "\n"
            
        idx_path = os.path.join(index_dir, f"{folder}_全記事一覧.md")
        with open(idx_path, "w", encoding="utf-8") as f:
            f.write(idx_content)
            
    # Update MOC to point to these new indexes
    with open(os.path.join(base_dir, f"{moc_file}.md"), "a", encoding="utf-8") as f:
        f.write("\n## 🔍 収集ソース別・全記事インデックス\n")
        for folder, desc in sources.items():
            f.write(f"- [[{folder}_全記事一覧|{desc}]]\n")

if __name__ == "__main__":
    beautify_specialized_notes()
    standardize_all_articles()
    create_thematic_indexes()
    print("Vault organization finalized.")
