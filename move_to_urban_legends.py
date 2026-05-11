# -*- coding: utf-8 -*-
import os
import shutil
import glob

base_vault = "/Users/masashi/Documents/Obsidian Vault/理論・研究"

# 新しい都市伝説専門ノートのルートフォルダ
urban_dir = os.path.join(base_vault, "06_信仰・霊性", "都市伝説・偽書_専門ノート")
os.makedirs(urban_dir, exist_ok=True)

# 1. マスターノート（専門ノート）の作成
master_note_path = os.path.join(urban_dir, "🎓 都市伝説と偽書の概論_根拠なき伝承の系譜.md")
master_content = """---
title: "都市伝説と偽書の概論_根拠なき伝承の系譜"
tags: [都市伝説, 偽書, オカルト, 神代文字, 古史古伝]
---

# 🎓 都市伝説と偽書の概論_根拠なき伝承の系譜
> [!abstract] このノートの概要
> このページは、学術的な歴史的根拠に乏しい「偽書（古史古伝）」「神代文字」「歴史ミステリー・陰謀論」、および現代の「ネット怪異」などを集約した専門ノートです。

> [!info] 基礎知識
### なぜ「根拠の乏しいもの」を分けるのか
歴史研究において、史料批判を通過した正史（『日本書紀』や『六国史』など）や考古学的物証と、江戸時代以降の創作や近代のオカルト思想（古史古伝や神代文字など）を混同することは、研究のノイズとなります。
しかし、これらの「根拠なき伝承」もまた、当時の人々が「歴史をどう解釈したかったか（ナショナリズムやコンプレックスの裏返し）」を示す重要な民俗学的・思想史的資料です。

### 分類される主なカテゴリ
- **古史古伝**: 『竹内文書』『東日流外三郡誌』など、宇宙創造や超古代文明を語る偽書群。
- **神代文字**: カタカムナ、ヲシテ文字など、上代特殊仮名遣の法則を無視した近世以降の創作文字。
- **歴史ミステリー**: 「神武天皇＝徐福説」「日ユ同祖論」「剣山のアーク」などのオカルト的仮説。
- **ネット怪異**: 「きさらぎ駅」「八尺様」など、現代の神隠し・呪術伝説。

---
[[00_古代史研究アーカイブ_MOC|🔙 研究アーカイブ目次に戻る]]
"""
with open(master_note_path, 'w', encoding='utf-8') as f:
    f.write(master_content)

# 2. 移動対象の定義と移動
# a. 既存の都市伝説・ミステリーフォルダ
old_urban = os.path.join(base_vault, "06_信仰・霊性", "都市伝説_ミステリー")
if os.path.exists(old_urban):
    for item in os.listdir(old_urban):
        shutil.move(os.path.join(old_urban, item), os.path.join(urban_dir, item))
    os.rmdir(old_urban)

# b. 古史古伝と神代文字（学術的根拠に乏しい偽書・創作文字）
koshikoden = os.path.join(base_vault, "04_神話・古典解読", "古史古伝_専門ノート")
if os.path.exists(koshikoden):
    shutil.move(koshikoden, os.path.join(urban_dir, "古史古伝_偽書群"))

kamiyomoji = os.path.join(base_vault, "04_神話・古典解読", "神代文字_専門ノート")
if os.path.exists(kamiyomoji):
    shutil.move(kamiyomoji, os.path.join(urban_dir, "神代文字_オカルト・超科学"))

# c. 歴史ミステリー・根拠の乏しい仮説（個別ファイル）
speculative_files = [
    "神武天皇＝徐福説の真偽とロマン.md",
    "富士王朝と宮下文書_もう一つの徐福伝説.md",
    "三種の神器と阿波の秘宝伝説.md" # 剣山アーク伝説などを含む場合
]

mystery_dir = os.path.join(urban_dir, "歴史ミステリー_飛躍した仮説")
os.makedirs(mystery_dir, exist_ok=True)

for fname in speculative_files:
    search_path = os.path.join(base_vault, "**", fname)
    matches = glob.glob(search_path, recursive=True)
    for match in matches:
        if not "都市伝説・偽書_専門ノート" in match: # 既に移動したものは除く
            shutil.move(match, os.path.join(mystery_dir, os.path.basename(match)))

print("Successfully isolated unverified/urban legend files into the new specialized directory.")
