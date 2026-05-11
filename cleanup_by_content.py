import os
import glob

# Directory for marine816 posts
target_dir = "/Users/masashi/Documents/Obsidian Vault/資料/Web_Archives/ameblo_marine816"

# Aquarium-related keywords
aqua_keywords = [
    "水槽", "サンゴ", "チョウチョウウオ", "ヤッコ", "カクレクマノミ", "水換え", 
    "プロテインスキマー", "ライブロック", "海水魚", "クーラー", "ヒーター", "照明",
    "LED", "レイアウト", "白点病", "キュプラミン", "ろ過", "フィルター", "添加剤",
    "餌", "給餌", "水質", "比重", "水温", "マメスナ"
]

# History/Mythology-related keywords (Safe words to prevent deletion)
history_keywords = [
    "天皇", "古事記", "日本書紀", "神社", "古墳", "阿波", "邪馬台国", "魏志倭人伝",
    "卑弥呼", "徐福", "遺跡", "出雲", "大和", "神話", "命", "尊", "考察", "比定",
    "ヤマト", "国生み"
]

def should_delete(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Count occurrences of aquarium keywords
        aqua_count = sum(content.count(kw) for kw in aqua_keywords)
        
        # Count occurrences of history keywords
        history_count = sum(content.count(kw) for kw in history_keywords)
        
        # If it has significant aquarium talk and almost no history talk, delete it.
        # Threshold: More than 5 aquarium keywords and 0 history keywords,
        # OR the title itself is just "水槽" related and no history words exist.
        
        if history_count == 0 and aqua_count > 2:
            return True
            
        # If it's overwhelmingly about aquariums
        if aqua_count > 10 and history_count < 2:
            return True

        return False
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return False

total_deleted = 0
files = glob.glob(os.path.join(target_dir, "*.md"))

for file_path in files:
    if should_delete(file_path):
        try:
            os.remove(file_path)
            print(f"Deleted (Content match): {os.path.basename(file_path)}")
            total_deleted += 1
        except Exception as e:
            print(f"Failed to delete {file_path}: {e}")

print(f"\nTotal files deleted based on content: {total_deleted}")
