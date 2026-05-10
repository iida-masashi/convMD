# -*- coding: utf-8 -*-
import os
import glob
import re

base_dir = "/Users/masashi/Documents/Obsidian Vault/資料/Web_Archives"

# Updated definition with more robust keywords and synonyms
specialized_links = {
    "阿波説の概論_なぜ徳島が日本の起源とされるのか": ["阿波", "徳島", "高天原", "天孫降臨", "忌部", "不比等", "歴史隠蔽"],
    "邪馬台国阿波説と若杉山辰砂採掘遺跡": ["邪馬台国", "魏志倭人伝", "卑弥呼", "辰砂", "水銀朱", "若杉山", "阿南市"],
    "阿波忌部氏と大嘗祭の麁服（あらたえ）": ["大嘗祭", "麁服", "あらたえ", "忌部氏", "三木家", "美馬市"],
    "高天原と天孫降臨_剣山に隠された神話": ["剣山", "天孫降臨", "大宜都比売", "神山町", "オノゴロ", "天の岩戸"],
    "徐福伝説の基本と歴史的背景": ["徐福", "始皇帝", "蓬莱", "不老不死"],
    "新宮の徐福伝説_熊野に辿り着いた一行": ["新宮", "熊野", "阿須賀神社", "天台烏薬"],
    "富士王朝と宮下文書_もう一つの徐福伝説": ["宮下文書", "富士王朝", "富士古文書", "阿祖山"],
    "神武天皇＝徐福説の真偽とロマン": ["神武", "徐福", "東征"],
    "古史古伝の概要と歴史的背景": ["古史古伝", "九鬼文書", "上記", "ウガヤフキアエズ", "偽書"],
    "ホツマツタヱ_五七調で記された真の歴史": ["ホツマツタヱ", "ミカサフミ", "フトマニ", "秀真", "アマテル"],
    "東日流外三郡誌_東北の古代独立王国": ["東日流外三郡誌", "アラハバキ", "安東氏", "津軽"],
    "神代文字の概論と研究史_徹底解説": ["神代文字", "平田篤胤", "神字日文伝", "言霊"],
    "阿比留文字と阿比留草文字_対馬伝来の謎": ["阿比留", "アヒル草", "対馬", "ハングル"],
    "ヲシテ文字_五元素とホツマツタヱの宇宙観": ["ヲシテ文字", "アワの歌", "アワのうた", "秀真文字"],
    "カタカムナ文字_潜象界の物理とウタヒ": ["カタカムナ", "楢崎皐月", "ウタヒ", "潜象界", "六甲山"],
    "出雲文字と豊国文字_その他の神代文字": ["出雲文字", "豊国文字", "琉球文字", "アイヌ文字"],
    "日ユ同祖論_古代イスラエルと日本の繋がり": ["日ユ同祖論", "イスラエル", "ユダヤ", "契約の箱", "10支族"],
    "剣山ソロモンの秘宝伝説": ["ソロモン", "秘宝", "アーク", "高根正教", "剣山"],
    "八咫烏と裏天皇の都市伝説": ["八咫烏", "裏天皇", "秘密結社", "加茂", "サンカ"],
    "竹内文書と超古代文明": ["竹内文書", "竹内巨麿", "超古代文明", "五色人", "キリストの墓"]
}

exclude_dirs = ["専門ノート", "都市伝説_ミステリー", "MOC"]

files = glob.glob(os.path.join(base_dir, "**/*.md"), recursive=True)
updated_count = 0

for file_path in files:
    if any(ex in file_path for ex in exclude_dirs) or "MOC" in file_path:
        continue

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract current links to avoid duplicates
        existing_links = re.findall(r'\[\[(.*?)\]\]', content)
        
        links_to_add = []
        for note_name, keywords in specialized_links.items():
            if note_name in existing_links:
                continue
            
            if any(kw in content for kw in keywords):
                links_to_add.append(f"- [[{note_name}]]")

        if links_to_add:
            # Check if section header already exists
            if "## 関連する専門ノート" in content:
                # Append only new links to existing section
                new_content = content.strip() + "\n" + "\n".join(links_to_add) + "\n"
            else:
                # Add new section
                new_content = content.strip() + "\n\n---\n## 関連する専門ノート\n" + "\n".join(links_to_add) + "\n"
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            updated_count += 1
            
    except Exception as e:
        print(f"Error on {file_path}: {e}")

print(f"Refined links for {updated_count} files.")
