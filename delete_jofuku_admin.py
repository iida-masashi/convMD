# -*- coding: utf-8 -*-
import os
import glob

base_dir = "/Users/masashi/Documents/Obsidian Vault/資料/Web_Archives/jofuku_or_jp"

files_to_delete = [
    "活動記録_財団法人新宮徐福協会.md",
    "園内紹介_財団法人新宮徐福協会.md",
    "活動記録.md",
    "免責事項_財団法人新宮徐福協会.md",
    "設立概要_財団法人新宮徐福協会.md"
]

total_deleted = 0

for filename in files_to_delete:
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
