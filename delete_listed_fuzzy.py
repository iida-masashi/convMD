import os
import glob

base_dir = "/Users/masashi/Documents/Obsidian Vault"

# Use wildcards to match the filenames more robustly, in case of slight variations (like encoded ampersands, spaces, etc.)
patterns_to_delete = [
    "*武と競技.md",
    "*身体と向き合う.md",
    "*言い換えると良い7つの言葉.md",
    "*節分であり大晦日であるという事.md",
    "*休むという事の意味と必要性と大切さ.md",
    "*習得が難しい言語を日常使いこなしている.md",
    "*語源を考える〜幸せ・人間〜.md",
    "*挨拶をするという事.md",
    "*日本から奪われたもの.md",
    "*死後の世界は文字で分かる日本語.md",
    "*これから必要になる指数とは？.md",
    "*人の呼び方.md",
    "*【添加物】事実と虚偽のお話.md",
    "*2026年1月16日（土）の日記.md",
    "*倫敦ノ山本五十六.md",
    "*なぜイギリスにスパイ小説作家が多いのか.md",
    "*なぜ作家の作風が変わるのか.md",
    "*「志ん輔」と「一之輔」を聴く.md",
    "*ニュー・エディション*.md",
    "*トレーナーの必要性.md",
    "*チャレンジする事.md",
    "*ディフェンス.md",
    "*前提。.md",
    "*距離と間合い.md",
    "*帯の質.md",
    "*停滞と成長.md",
    "*問題解決する為の見る５つの視点*.md",
    "*変化しない事を選んだ結果に待ち構えるもの.md",
    "*続・残していかなくてはならないもの.md",
    "*「オリジナル」と「カバー」を聴く.md",
    "*ドルフィーを聴く*.md",
    "*ツェッペリンを観る*.md",
    "*喬太郎を聴く*.md",
    "*ペッパー・アダムスを聴く*.md",
    "*マーラーを聴く*.md",
    "*ベートーヴェンを聴く*.md"
]

total_deleted = 0

for pattern in patterns_to_delete:
    search_path = os.path.join(base_dir, "**", pattern)
    matched_files = glob.glob(search_path, recursive=True)
    
    for file_path in matched_files:
        try:
            os.remove(file_path)
            print(f"Deleted: {os.path.basename(file_path)}")
            total_deleted += 1
        except Exception as e:
            print(f"Failed to delete {file_path}: {e}")

print(f"\nTotal files deleted: {total_deleted}")
