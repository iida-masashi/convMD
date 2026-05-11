import os
import glob

base_dir = "/Users/masashi/Documents/Obsidian Vault"

# List of filenames extracted from the provided markdown content
files_to_delete = [
    # Martial Arts
    "2020-07-29-武と競技.md",
    "2020-12-29-身体と向き合う.md",
    
    # Japanese Culture / Thoughts
    "2023-02-01-【言い換え】言い換えると良い7つの言葉.md",
    "2023-02-04-【日本・旧暦】節分であり大晦日であるという事.md",
    "2023-02-18-【休息・日本】休むという事の意味と必要性と大切さ.md",
    "2023-02-22-【日本・日本語】習得が難しい言語を日常使いこなしている.md",
    "2023-06-30-【日本・日本語】語源を考える〜幸せ・人間〜.md",
    "2023-07-31-【日本・日本語】挨拶をするという事.md",
    "2024-04-01-【日本・取り戻せ日本】日本から奪われたもの.md",
    "2026-05-01-【日本・日本語】死後の世界は文字で分かる日本語.md",
    
    # Lifestyle
    "2022-12-30-【あなたの指数はいくつ？】これから必要になる指数とは？.md",
    "2023-01-11-人の呼び方.md",
    "2023-01-25-【添加物】事実と虚偽のお話.md",
    "2026-01-17-2026年1月16日（土）の日記.md",
    
    # Hobbies
    "2021-12-31-【実況と感想】NHK太平洋戦争80年・特集ドラマ_倫敦ノ山本五十六.md",
    "2025-06-10-スパイ小説-１：なぜイギリスにスパイ小説作家が多いのか.md",
    "2025-07-01-スパイ小説-２：なぜ作家の作風が変わるのか.md",
    "2026-04-17-古典落語-４：「志ん輔」と「一之輔」を聴く.md",
    
    # Uncategorized / Others
    "2010-02-05-ニュー・エディション_-_If_It_Isn&amp;.md",
    "2020-06-09-トレーナーの必要性.md",
    "2020-06-11-チャレンジする事.md",
    "2020-06-15-ディフェンス.md",
    "2020-08-05-前提。.md",
    "2020-08-11-距離と間合い.md",
    "2020-08-14-帯の質.md",
    "2021-10-25-停滞と成長.md",
    "2023-01-26-【視点】問題解決する為の見る５つの視点～20230126～.md",
    "2023-02-28-【変化しない】変化しない事を選んだ結果に待ち構えるもの.md",
    "2023-05-30-続・残していかなくてはならないもの.md",
    "2025-07-29-「オリジナル」と「カバー」を聴く.md",
    "2025-08-20-ドルフィーを聴く_At_The_Five_Spot_Vol.2.md",
    "2025-09-28-ツェッペリンを観る：Becoming_Led-Zeppelin.md",
    "2025-10-07-喬太郎を聴く「鶏もつ煮込み」.md",
    "2026-01-18-ペッパー・アダムスを聴く：Live_at_the_Room_at_the_Top.md",
    "2026-02-06-マーラーを聴く：交響曲５番第４楽章-アダージェット.md",
    "2026-03-07-ベートーヴェンを聴く：弦楽四重奏曲.md"
]

total_deleted = 0

for filename in files_to_delete:
    # Use glob to find the file recursively anywhere in the vault
    search_path = os.path.join(base_dir, "**", filename)
    matched_files = glob.glob(search_path, recursive=True)
    
    for file_path in matched_files:
        try:
            os.remove(file_path)
            print(f"Deleted: {os.path.basename(file_path)}")
            total_deleted += 1
        except Exception as e:
            print(f"Failed to delete {file_path}: {e}")

print(f"\nTotal files deleted: {total_deleted}")
