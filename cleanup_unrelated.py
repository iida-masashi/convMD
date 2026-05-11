import os
import glob

# Base directory for the vault
base_dir = "/Users/masashi/Documents/Obsidian Vault/資料/Web_Archives"

# List of strings/keywords in filenames that indicate they should be deleted.
# We include specific filenames and patterns from the list provided earlier.
patterns_to_delete = [
    # --- marine816 (Aquarium / Daily / Shopping) ---
    "*サンゴ*.md", "*水槽*.md", "*チョウ*.md", "*水換え*.md", "*散財*.md",
    "*コケ*.md", "*ろ過*.md", "*照明*.md", "*クーラー*.md", "*キュプラミン*.md",
    "*添加剤*.md", "*ヤッコ*.md", "*カクレ*.md", "*ヒラムシ*.md", "*海水*.md",
    "*設備*.md", "*レッドのバブル*.md", "*ジョーズ*.md", "*ウルトラマン コラク*.md",
    "*隠れ家*.md", "*システムＬＥＤ*.md", "*クリスマス*.md", "*アケオメ*.md",
    "*お金って飛ぶ*.md", "*ぽぴぃ病*.md", "*タンクメイト*.md", "*給餌*.md",
    "*レイアウト変更*.md", "*アクア*.md", "*エルボ*.md", "*コラク*.md", "*ポチ*.md",
    "*水汲み*.md", "*オーストラリアからの刺客*.md", "*黄色い水*.md", "*ゾンビ*.md",
    "*ボーダーでイカすヤツ*.md", "*まさかの連投*.md", "*ぶるああぁ*.md", "*激おこ*.md",
    "*チョボチョボ*.md", "*今日*.md", "*昨日*.md", "*オォォ*.md", "*こんちくしょ*.md",
    "*スマン、狩りの時間*.md", "*変化*.md", "*家政婦*.md", "*小休止*.md", "*明暗*.md",
    "*新メンバー*.md", "*新入り*.md", "*春*.md", "*梅雨*.md", "*秋*.md", "*冬*.md",
    "*１０月*.md", "*９月*.md", "*６月*.md", "*１２月*.md", "*あけおめ*.md",
    "*あけましておめでとう*.md", "*奇跡*.md", "*復活*.md", "*忘れた頃*.md",
    "*悪癖*.md", "*慢性の病気*.md", "*病気治って*.md", "*オレの調子*.md",
    "*テンション*.md", "*ダウン*.md", "*やっとこさ*.md", "*あらよっと*.md",
    "*おっと忘れてた*.md", "*オイ、オマエ*.md", "*＾＾*.md", "*むぅ*.md", "*うーん*.md",
    "*ぃょぅ*.md", "*ハロウ*.md", "*なんやねん*.md", "*どうでっしゃろ*.md",
    "*みんなおせーて*.md", "*私です*.md", "*実は*.md", "*さてと*.md", "*その２.md",
    "*早速ですが*.md", "*本日の*.md", "*近況*.md", "*ここ１ヶ月*.md", "*いつもの.md",
    "*いつの間にか*.md", "*もう*.md", "*乗っけました*.md", "*追加*.md", "*買いマスタ*.md",
    "*ゲット*.md", "*達磨*.md", "*片目の魚*.md", "*星型の*.md", "*赤い*.md", "*赤.md",
    "*泳いできた*.md", "*張替え*.md", "*治療生活*.md",

    # --- rakujin_01 (Daily / Tech / Writing) ---
    "*バイクの話*.md", "*インカムのお話*.md", "*昇降デスク*.md", "*本を自分で作る*.md",
    "*AI検索*.md", "*フォロー・登録者を増やす*.md",

    # --- kikuchi2 (Modern Politics / Literature not strictly related) ---
    "*ヒトラー文字起こし*.md", "*大阪維新の会は大ウソつき*.md", "*秘密の部屋*.md",
    "*アイスクリーム*.md", "*史実と虚構の間*.md", "*カワウソと『円朝全集』*.md",
    "*紅葉*.md", "*円朝*.md", "*延広*.md"
]

total_deleted = 0
for pattern in patterns_to_delete:
    # Use glob to find all matching files recursively
    search_path = os.path.join(base_dir, "**", pattern)
    files = glob.glob(search_path, recursive=True)
    
    for file_path in files:
        if os.path.isfile(file_path):
            try:
                os.remove(file_path)
                print(f"Deleted: {os.path.basename(file_path)}")
                total_deleted += 1
            except Exception as e:
                print(f"Failed to delete {file_path}: {e}")

print(f"\nTotal files deleted: {total_deleted}")
