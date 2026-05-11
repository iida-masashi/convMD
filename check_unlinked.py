# -*- coding: utf-8 -*-
import os
import glob

base_dir = "/Users/masashi/Documents/Obsidian Vault/資料/Web_Archives"

# リストアップした専門ノート
specialized_notes = [
    "阿波説の概論_なぜ徳島が日本の起源とされるのか", "邪馬台国阿波説と若杉山辰砂採掘遺跡", "阿波忌部氏と大嘗祭の麁服（あらたえ）", "高天原と天孫降臨_剣山に隠された神話",
    "徐福伝説の基本と歴史的背景", "新宮の徐福伝説_熊野に辿り着いた一行", "富士王朝と宮下文書_もう一つの徐福伝説", "神武天皇＝徐福説の真偽とロマン",
    "古史古伝の概要と歴史的背景", "ホツマツタヱ_五七調で記された真の歴史", "東日流外三郡誌_東北の古代独立王国", "宮下文書（富士古文書）と徐福の影",
    "神代文字の概論と研究史_徹底解説", "阿比留文字と阿比留草文字_対馬伝来の謎", "ヲシテ文字_五元素とホツマツタヱの宇宙観", "カタカムナ文字_潜象界の物理とウタヒ", "出雲文字と豊国文字_その他の神代文字",
    "日ユ同祖論_古代イスラエルと日本の繋がり", "剣山ソロモンの秘宝伝説", "八咫烏と裏天皇の都市伝説", "竹内文書と超古代文明",
    "平将門の首塚の祟り", "かごめかごめの隠された意味", "丑の刻参りと呪術の歴史",
    "きさらぎ駅_異界への迷い込み", "八尺様_魅入られたら逃げられない怪異", "コトリバコ_呪いの箱"
]

# 専門ノートのフォルダやMOC自体は除外
exclude_dirs = ["専門ノート", "都市伝説_ミステリー", "00_古代史研究アーカイブ_MOC.md"]

files = glob.glob(os.path.join(base_dir, "**/*.md"), recursive=True)
unlinked_files = []

for file_path in files:
    if any(ex in file_path for ex in exclude_dirs):
        continue

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 専門ノートのリンクが含まれているかチェック
        has_link = False
        for note in specialized_notes:
            if f"[[{note}]]" in content:
                has_link = True
                break
        
        if not has_link:
            unlinked_files.append(file_path)

    except Exception as e:
        print(f"Error reading {file_path}")

print(f"Total unlinked files: {len(unlinked_files)}")
print("-" * 40)
for f in unlinked_files[:50]:
    # フォルダ名を含めて少し見やすく表示
    rel_path = os.path.relpath(f, base_dir)
    print(rel_path)

if len(unlinked_files) > 50:
    print(f"... 他 {len(unlinked_files) - 50} 件")
