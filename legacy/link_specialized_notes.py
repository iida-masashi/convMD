# -*- coding: utf-8 -*-
import os
import glob

base_dir = "/Users/masashi/Documents/Obsidian Vault/資料/Web_Archives"

# 定義：各専門ノートと、それを紐づけるためのキーワード
specialized_links = {
    "阿波説の概論_なぜ徳島が日本の起源とされるのか": ["阿波", "徳島", "高天原", "天孫降臨", "忌部"],
    "邪馬台国阿波説と若杉山辰砂採掘遺跡": ["邪馬台国", "魏志倭人伝", "卑弥呼", "辰砂", "水銀朱", "若杉山"],
    "阿波忌部氏と大嘗祭の麁服（あらたえ）": ["大嘗祭", "麁服", "あらたえ", "忌部氏"],
    "高天原と天孫降臨_剣山に隠された神話": ["剣山", "天孫降臨", "大宜都比売", "神山町"],
    "徐福伝説の基本と歴史的背景": ["徐福", "始皇帝", "天台烏薬", "蓬莱"],
    "新宮の徐福伝説_熊野に辿り着いた一行": ["新宮", "熊野", "阿須賀神社", "天台烏薬"],
    "富士王朝と宮下文書_もう一つの徐福伝説": ["宮下文書", "富士王朝", "富士古文書"],
    "古史古伝の概要と歴史的背景": ["古史古伝", "九鬼文書", "上記", "ウガヤフキアエズ"],
    "ホツマツタヱ_五七調で記された真の歴史": ["ホツマツタヱ", "ミカサフミ", "フトマニ"],
    "東日流外三郡誌_東北の古代独立王国": ["東日流外三郡誌", "アラハバキ", "安東氏"],
    "神代文字の概論と研究史_徹底解説": ["神代文字", "平田篤胤", "神字日文伝"],
    "阿比留文字と阿比留草文字_対馬伝来の謎": ["阿比留", "アヒル草", "対馬"],
    "ヲシテ文字_五元素とホツマツタヱの宇宙観": ["ヲシテ文字", "アワの歌", "秀真文字"],
    "カタカムナ文字_潜象界の物理とウタヒ": ["カタカムナ", "楢崎皐月", "ウタヒ", "潜象界"],
    "出雲文字と豊国文字_その他の神代文字": ["出雲文字", "豊国文字", "琉球文字"],
    "日ユ同祖論_古代イスラエルと日本の繋がり": ["日ユ同祖論", "イスラエル", "ユダヤ", "契約の箱"],
    "剣山ソロモンの秘宝伝説": ["ソロモン", "秘宝", "アーク", "高根正教"],
    "八咫烏と裏天皇の都市伝説": ["八咫烏", "裏天皇", "秘密結社"],
    "竹内文書と超古代文明": ["竹内文書", "竹内巨麿", "超古代文明", "五色人"]
}

# 専門ノート自体のフォルダは除外する
exclude_dirs = ["専門ノート", "都市伝説_ミステリー"]

files = glob.glob(os.path.join(base_dir, "**/*.md"), recursive=True)

linked_count = 0

for file_path in files:
    # 専門ノートフォルダ内のファイルはスキップ
    if any(ex in file_path for ex in exclude_dirs):
        continue

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # すでに「関連する専門ノート」という見出しがあれば、処理済みとしてスキップ
        if "## 関連する専門ノート" in content:
            continue

        links_to_add = []
        
        # 本文中のキーワードをチェック
        for note_name, keywords in specialized_links.items():
            # その専門ノートへのリンクがすでに本文に存在するかチェック
            if f"[[{note_name}]]" in content:
                continue
                
            if any(kw in content for kw in keywords):
                links_to_add.append(f"- [[{note_name}]]")
        
        # 該当するキーワードがあれば、末尾にリンクを追記する
        if links_to_add:
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write("\n\n---\n## 関連する専門ノート\n")
                f.write("\n".join(links_to_add))
                f.write("\n")
            linked_count += 1
            
    except Exception as e:
        print(f"Error processing {file_path}: {e}")

print(f"\nSuccessfully linked {linked_count} files to specialized notes.")
