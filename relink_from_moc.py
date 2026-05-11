# -*- coding: utf-8 -*-
import os
import glob
import re

base_dir = "/Users/masashi/Documents/Obsidian Vault/資料/Web_Archives"
moc_path = os.path.join(base_dir, "00_古代史研究アーカイブ_MOC.md")

# 1. 索引(MOC)の削除
if os.path.exists(moc_path):
    os.remove(moc_path)
    print(f"Deleted MOC: {moc_path}")

# 2. 未リンク記事の救済用・広範な専門ノートを新設
spec_notes_dir = os.path.join(base_dir, "その他_専門ノート")
os.makedirs(spec_notes_dir, exist_ok=True)

catch_all_notes = {
    "古墳時代と古代国家の成り立ち": {
        "tags": ["古墳時代", "飛鳥時代", "古代史", "国家形成"],
        "content": "# 🎓 古墳時代と古代国家の成り立ち\n> [!abstract] このノートの概要\n> このページは、古墳時代から飛鳥時代にかけての国家形成、氏族の動向、遺跡に関する専門的なまとめノートです。\n\n> [!info] 基礎知識\n### 古墳時代とは\n3世紀半ばから7世紀にかけての、前方後円墳をはじめとする古墳が盛んに造営された時代。大和王権が国内を統一していく過程であり、蘇我氏や物部氏といった有力豪族が台頭した。\n\n### 重要なテーマ\n- 古墳の分布と権力の変遷\n- 飛鳥時代の政治改革（大化の改新など）と天皇家の確立"
    },
    "神社信仰と古墳の歴史的意義": {
        "tags": ["神社", "古墳", "祭祀", "古代史"],
        "content": "# 🎓 神社信仰と古墳の歴史的意義\n> [!abstract] このノートの概要\n> このページは、日本各地の神社や古墳の成り立ち、そしてそれらが持つ歴史的・祭祀的な意義についての専門的なまとめノートです。\n\n> [!info] 基礎知識\n### 神社と古墳の繋がり\n古代の権力者の墓である古墳と、神を祀る神社は密接に結びついていることが多い。古い古墳の跡地に神社が建てられたり、地域の豪族の祖霊が氏神として祀られたりすることで、信仰の場が形成されてきた。\n阿波（徳島）などの特定の地域には、記紀神話の神々を祀る特異な古社が密集しており、古代史の謎を解く鍵となっている。"
    },
    "記紀神話と古代日本の建国": {
        "tags": ["古事記", "日本書紀", "神話", "建国"],
        "content": "# 🎓 記紀神話と古代日本の建国\n> [!abstract] このノートの概要\n> このページは、『古事記』『日本書紀』に記された神話と、実際の古代日本の建国過程についての専門的なまとめノートです。\n\n> [!info] 基礎知識\n### 記紀神話の構造\n国生み、神生みから始まり、天孫降臨、神武東征を経て、大和朝廷の成立に至る壮大なストーリー。これらは単なるおとぎ話ではなく、当時の政治的意図（藤原氏や天武天皇の正当化）や、各地方の豪族の伝承を統合したものである。\n神話の裏に隠された「真の歴史（阿波起源説など）」を読み解くことが、古代史研究の醍醐味である。"
    },
    "東国古代史と香取海の神々": {
        "tags": ["東国", "香取海", "鹿島神宮", "香取神宮"],
        "content": "# 🎓 東国古代史と香取海の神々\n> [!abstract] このノートの概要\n> このページは、古代の関東地方（東国）に存在した「香取海（かとりのうみ）」と、その周辺の信仰に関する専門的なまとめノートです。\n\n> [!info] 基礎知識\n### 香取海とは\n古代の関東平野に大きく広がっていた内海。現在の霞ヶ浦や印旛沼、手賀沼などが繋がった巨大な水域であった。\nこの周辺には、鹿島神宮や香取神宮といったヤマト王権の東国前線基地としての重要拠点が置かれ、タケミカヅチやフツヌシといった強力な武神が祀られている。東国開拓の歴史を紐解く上で極めて重要な地域である。"
    }
}

for title, data in catch_all_notes.items():
    path = os.path.join(spec_notes_dir, f"{title}.md")
    with open(path, 'w', encoding='utf-8') as f:
        f.write(f"---\ntitle: \"{title}\"\ntags: [{', '.join(data['tags'])}]\n---\n\n{data['content']}\n")
print("Created fallback specialized notes.")

# フォルダごとに、未リンクファイルに付与するデフォルトの専門ノートを定義
dir_to_spec = {
    "note_kofunjidaishi": "古墳時代と古代国家の成り立ち",
    "kohun-jinjya_blog": "神社信仰と古墳の歴史的意義",
    "note_rakujin_01": "記紀神話と古代日本の建国",
    "kamimasu_com": "東国古代史と香取海の神々",
    "ameblo_marine816": "阿波説の概論_なぜ徳島が日本の起源とされるのか",
    "note_kometake": "高天原と天孫降臨_剣山に隠された神話",
    "kikuchi2": "六国史と古代の正史",
    "jofuku_or_jp": "徐福伝説の基本と歴史的背景"
}

# 3. すべてのMDファイルからMOCへのリンクを消去し、専門ノートへリンクし直す
all_mds = glob.glob(os.path.join(base_dir, "**/*.md"), recursive=True)

# 存在するすべての専門ノートの名前をリストアップ（リンク判定用）
spec_notes_names = []
for p in all_mds:
    if "専門ノート" in p:
        name = os.path.basename(p).replace(".md", "")
        spec_notes_names.append(name)

for title in catch_all_notes.keys():
    if title not in spec_notes_names:
        spec_notes_names.append(title)

updated_count = 0
relinked_count = 0

for file_path in all_mds:
    # 専門ノートやインデックス自体は対象外だが、MOCへの戻りリンクの削除だけ行う
    if "専門ノート" in file_path or "99_インデックス" in file_path:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        new_content = re.sub(r'\n?---\n\[\[00_古代史研究アーカイブ_MOC\|🔙 研究アーカイブ目次に戻る\]\]\n?', '', content)
        if new_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
        continue

    # 個別の記事ファイル
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content

    # MOCリンクのブロックを削除
    content = re.sub(r'\n?> \[!link\] 関連リソース\n> - \[\[00_古代史研究アーカイブ_MOC\|📁 研究アーカイブ目次 \(MOC\)\]\]\n?', '', content)
    content = re.sub(r'\n?---\n\s*$', '\n', content) # 末尾の余分な横線を削除

    # 既にいずれかの専門ノートにリンクされているかチェック
    has_spec_link = False
    for spec_name in spec_notes_names:
        if f"[[{spec_name}]]" in content or f"[[{spec_name}|" in content:
            has_spec_link = True
            break
            
    # どの専門ノートにもリンクされていない場合、親フォルダに応じたデフォルトの専門ノートを付与
    if not has_spec_link:
        parent_dir = os.path.dirname(file_path)
        fallback_note = None
        for dir_key, note_name in dir_to_spec.items():
            if dir_key in parent_dir:
                fallback_note = note_name
                break
        
        if fallback_note:
            if "## 関連する専門ノート" in content:
                content += f"- [[{fallback_note}]]\n"
            else:
                content = content.strip() + f"\n\n---\n## 関連する専門ノート\n- [[{fallback_note}]]\n"
            relinked_count += 1

    content = content.strip() + '\n'

    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        updated_count += 1

print(f"Removed MOC links from {updated_count} files.")
print(f"Re-linked {relinked_count} orphaned files to specialized notes.")
