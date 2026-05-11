# -*- coding: utf-8 -*-
import os
import glob

base_dir = "/Users/masashi/Documents/Obsidian Vault/資料/Web_Archives"

# Step 1: Add internal cross-links to specialized notes
cross_links = {
    "阿波説の概論_なぜ徳島が日本の起源とされるのか": [
        "邪馬台国阿波説と若杉山辰砂採掘遺跡",
        "阿波忌部氏と大嘗祭の麁服（あらたえ）",
        "高天原と天孫降臨_剣山に隠された神話",
        "剣山ソロモンの秘宝伝説"
    ],
    "徐福伝説の基本と歴史的背景": [
        "新宮の徐福伝説_熊野に辿り着いた一行",
        "富士王朝と宮下文書_もう一つの徐福伝説",
        "神武天皇＝徐福説の真偽とロマン",
        "宮下文書（富士古文書）と徐福の影"
    ],
    "神代文字の概論と研究史_徹底解説": [
        "阿比留文字と阿比留草文字_対馬伝来の謎",
        "ヲシテ文字_五元素とホツマツタヱの宇宙観",
        "カタカムナ文字_潜象界の物理とウタヒ",
        "ホツマツタヱ_五七調で記された真の歴史"
    ],
    "古史古伝の概要と歴史的背景": [
        "ホツマツタヱ_五七調で記された真の歴史",
        "宮下文書（富士古文書）と徐福の影",
        "竹内文書と超古代文明"
    ]
}

def add_cross_links():
    for source_note, targets in cross_links.items():
        # Find the source file path
        search_path = os.path.join(base_dir, "**", f"{source_note}.md")
        source_files = glob.glob(search_path, recursive=True)
        
        for source_file in source_files:
            with open(source_file, 'a', encoding='utf-8') as f:
                f.write("\n\n---\n## 関連する専門分野の深掘り\n")
                for target in targets:
                    f.write(f"- [[{target}]]\n")
            print(f"Added cross-links to: {source_note}")

# Step 2: Create a Master Map of Content (MOC)
def create_moc():
    moc_content = """---
title: "古代史・都市伝説 研究アーカイブ MOC"
tags: [MOC, index, 歴史, 阿波, 都市伝説]
---

# 古代史・都市伝説 研究アーカイブ

このページは、収集したウェブ記事や専門ノートを横断的に検索するための地図（Map of Content）です。

## 🏛️ 阿波説・古代日本
- [[阿波説の概論_なぜ徳島が日本の起源とされるのか]]
- [[邪馬台国阿波説と若杉山辰砂採掘遺跡]]
- [[高天原と天孫降臨_剣山に隠された神話]]
- [[阿波忌部氏と大嘗祭の麁服（あらたえ）]]

## 📜 古史古伝・神代文字
- [[古史古伝の概要と歴史的背景]]
- [[ホツマツタヱ_五七調で記された真の歴史]]
- [[宮下文書（富士古文書）と徐福の影]]
- [[神代文字の概論と研究史_徹底解説]]
- [[ヲシテ文字_五元素とホツマツタヱの宇宙観]]
- [[カタカムナ文字_潜象界の物理とウタヒ]]

## 🚢 徐福伝説・渡来
- [[徐福伝説の基本と歴史的背景]]
- [[新宮の徐福伝説_熊野に辿り着いた一行]]
- [[神武天皇＝徐福説の真偽とロマン]]

## 👺 都市伝説・ミステリー
- [[剣山ソロモンの秘宝伝説]]
- [[八咫烏と裏天皇の都市伝説]]
- [[日ユ同祖論_古代イスラエルと日本の繋がり]]
- [[竹内文書と超古代文明]]
- [[平将門の首塚の祟り]]

---
## 📂 収集ソース別フォルダ
- [[ameblo_marine816]] (Amebaブログ考察)
- [[note_kofunjidaishi]] (古墳時代史)
- [[note_rakujin_01]] (日本古代史)
- [[kikuchi2]] (菊池氏・古典資料)
- [[jofuku_or_jp]] (新宮徐福協会)
"""
    moc_path = os.path.join(base_dir, "00_古代史研究アーカイブ_MOC.md")
    with open(moc_path, "w", encoding="utf-8") as f:
        f.write(moc_content)
    print(f"Created MOC: {moc_path}")

if __name__ == "__main__":
    add_cross_links()
    create_moc()
