# -*- coding: utf-8 -*-
import os
import glob
import re

base_dir = "/Users/masashi/Documents/Obsidian Vault/資料/Web_Archives"
index_file = os.path.join(base_dir, "99_インデックス", "kikuchi2_全記事一覧.md")
moc_file = os.path.join(base_dir, "00_古代史研究アーカイブ_MOC.md")

# 1. 索引ファイルを削除
if os.path.exists(index_file):
    os.remove(index_file)
    print(f"Deleted {index_file}")

# 2. MOCから索引へのリンクを削除し、新しい専門ノートの項目を追加
if os.path.exists(moc_file):
    with open(moc_file, 'r', encoding='utf-8') as f:
        moc_content = f.read()
    
    # 既存のリンクを削除
    moc_content = re.sub(r'- \[\[kikuchi2_全記事一覧\|.*?\]\]\n?', '', moc_content)
    
    # 新しい専門ノートカテゴリの追加（まだなければ）
    if "## 📚 古典文学・正史" not in moc_content:
        addition = "\n## 📚 古典文学・正史\n- [[六国史と古代の正史]]\n- [[平家物語と源平盛衰記の概論]]\n"
        moc_content = moc_content.replace("## 🔍 収集ソース別・全記事インデックス", addition + "\n## 🔍 収集ソース別・全記事インデックス")
        
    with open(moc_file, 'w', encoding='utf-8') as f:
        f.write(moc_content)
    print("Updated MOC")

# 3. 菊池氏アーカイブの大量の平家物語・六国史に対応するための専用の「専門ノート」を新設
kikuchi_notes_dir = os.path.join(base_dir, "古典文学_専門ノート")
os.makedirs(kikuchi_notes_dir, exist_ok=True)

new_notes = {
    "六国史と古代の正史": {
        "tags": ["六国史", "日本書紀", "続日本紀", "古典資料"],
        "content": "# 🎓 六国史と古代の正史\n> [!abstract] このノートの概要\n> このページは、古代史・ミステリー研究アーカイブにおける専門的なまとめノートです。\n\n> [!info] 基礎知識\n### 六国史とは\n飛鳥時代から平安時代前期にかけて編纂された6つの勅撰修史（国家の正式な歴史書）の総称。\n1. 『日本書紀』\n2. 『続日本紀』\n3. 『日本後紀』\n4. 『続日本後紀』\n5. 『日本文徳天皇実録』\n6. 『日本三代実録』\n\nこれらは古代国家の公式記録であり、古史古伝や阿波説などの考察を行う上でも「表の歴史」として比較対照される重要な一次資料である。\n\n---\n[[00_古代史研究アーカイブ_MOC|🔙 研究アーカイブ目次に戻る]]"
    },
    "平家物語と源平盛衰記の概論": {
        "tags": ["平家物語", "源平盛衰記", "鎌倉時代", "古典文学"],
        "content": "# 🎓 平家物語と源平盛衰記の概論\n> [!abstract] このノートの概要\n> このページは、古代史・ミステリー研究アーカイブにおける専門的なまとめノートです。\n\n> [!info] 基礎知識\n### 概要\n鎌倉時代に成立した軍記物語の双璧。\n- **平家物語**: 平家の栄華と没落を描き、琵琶法師によって語り継がれた。語り本系（流布本、高野本）と読み本系（延慶本、長門本）など多数の異本が存在する。\n- **源平盛衰記**: 平家物語の異本の一つともされるが、より歴史的・説話的な記述が豊富で、全48巻に及ぶ長大な読み物となっている。\n\n---\n[[00_古代史研究アーカイブ_MOC|🔙 研究アーカイブ目次に戻る]]"
    }
}

for title, data in new_notes.items():
    note_path = os.path.join(kikuchi_notes_dir, f"{title}.md")
    with open(note_path, 'w', encoding='utf-8') as f:
        f.write(f"---\ntitle: \"{title}\"\ntags: [{', '.join(data['tags'])}]\n---\n\n{data['content']}")

# 4. kikuchi2フォルダ内のファイルを既存＆新設の専門ノートにリンクし直す
specialized_links = {
    "六国史と古代の正史": ["六国史", "三代実録", "日本書紀", "続日本紀", "後紀", "文徳天皇"],
    "平家物語と源平盛衰記の概論": ["平家物語", "源平盛衰記", "高野本", "延慶本", "長門本", "流布本", "承久記", "平治物語", "保元物語"],
    "平将門の首塚の祟り": ["将門記"],
    "古史古伝の概要と歴史的背景": ["栄花物語", "大鏡", "水鏡", "増鏡", "神皇正統記"], 
}

kikuchi_files = glob.glob(os.path.join(base_dir, "kikuchi2", "**/*.md"), recursive=True)
linked_count = 0

for file_path in kikuchi_files:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    existing_links = re.findall(r'\[\[(.*?)\]\]', content)
    links_to_add = []
    
    # ファイル名またはコンテンツからキーワードを判定
    for note_name, keywords in specialized_links.items():
        if note_name in existing_links:
            continue
        if any(kw in os.path.basename(file_path) or kw in content for kw in keywords):
            links_to_add.append(f"- [[{note_name}]]")

    if links_to_add:
        # フッターの直前にリンクを挿入する
        parts = content.split("---\n> [!link] 関連リソース")
        if len(parts) == 2:
            new_content = parts[0].strip() + "\n\n---\n## 関連する専門ノート\n" + "\n".join(links_to_add) + "\n\n---\n> [!link] 関連リソース" + parts[1]
        else:
            # 古いフォーマットの場合
            new_content = content.strip() + "\n\n---\n## 関連する専門ノート\n" + "\n".join(links_to_add) + "\n"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        linked_count += 1

print(f"Successfully relinked {linked_count} files in kikuchi2 to specialized notes.")
