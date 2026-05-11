# -*- coding: utf-8 -*-
import os
import glob

base_dir = "/Users/masashi/Documents/Obsidian Vault/資料/Web_Archives"

specialized_links = {
    "阿波説の概論_なぜ徳島が日本の起源とされるのか": ["阿波説", "徳島起源", "歴史隠蔽", "不比等"],
    "邪馬台国阿波説_水行十日陸行一月の真のルート": ["邪馬台国", "水行十日", "陸行一月", "魏志倭人伝", "伊都国", "投馬国"],
    "若杉山辰砂採掘遺跡_魏志倭人伝の「丹」の供給源": ["若杉山", "辰砂", "水銀朱", "阿南市", "丹"],
    "高天原の実在証明_徳島県神山町と延喜式内社の密集": ["高天原", "神山町", "大粟山", "天岩戸", "延喜式内社"],
    "剣山（鶴亀山）と天孫降臨_古代山岳信仰の聖地": ["剣山", "天孫降臨", "鶴亀山", "磐座", "アーク"],
    "神武東征の出発地は日向（宮崎）ではなく南阿波説": ["神武東征", "日向", "南阿波", "長国", "速吸の門", "紀伊水道"],
    "阿波忌部氏の歴史と産業_麻・穀・紙が支えた古代王権": ["阿波忌部", "忌部氏", "天日鷲命", "安房", "黒潮"],
    "大嘗祭と麁服（あらたえ）_天皇即位に必須の阿波の神布": ["大嘗祭", "麁服", "あらたえ", "三木家", "悠紀殿", "主基殿"]
}

exclude_dirs = ["専門ノート", "都市伝説_ミステリー", "MOC"]
files = glob.glob(os.path.join(base_dir, "**/*.md"), recursive=True)

for file_path in files:
    if any(ex in file_path for ex in exclude_dirs) or "MOC" in file_path:
        continue
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content
    links_to_add = []

    for note_name, keywords in specialized_links.items():
        if f"[[{note_name}]]" not in content and any(kw in content for kw in keywords):
            links_to_add.append(f"- [[{note_name}]]")

    if links_to_add:
        if "## 関連する専門ノート" in content:
            # 関連リソースの前に挿入
            parts = content.split("---\n> [!link] 関連リソース")
            if len(parts) == 2:
                content = parts[0].strip() + "\n" + "\n".join(links_to_add) + "\n\n---\n> [!link] 関連リソース" + parts[1]
        else:
            parts = content.split("---\n> [!link] 関連リソース")
            if len(parts) == 2:
                content = parts[0].strip() + "\n\n---\n## 関連する専門ノート\n" + "\n".join(links_to_add) + "\n\n---\n> [!link] 関連リソース" + parts[1]

    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

print("Re-linked articles to the newly expanded Awa Theory notes.")
