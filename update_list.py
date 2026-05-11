# -*- coding: utf-8 -*-
import os

file_path = "/Users/masashi/Documents/Obsidian Vault/理論・研究/99_管理/非研究対象ファイル候補一覧.md"

if not os.path.exists(file_path):
    print("File not found")
else:
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    new_lines = []
    for line in lines:
        if line.startswith("# 神社・歴史に関係ない可能性のあるファイル一覧"):
            new_lines.append(line)
            new_lines.append("\n> [!check] ステータス：処理完了（すべて削除済み・存在せず）\n> 2026年5月11日：Vault内を全体検索した結果、ここにリストアップされているファイル群はすでに削除されている、もしくは現在のVault内に存在しないことが確認されました。\n")
        elif line.startswith("- "):
            # Strike through the list items
            item = line[2:].strip()
            new_lines.append(f"- ~~{item}~~\n")
        else:
            new_lines.append(line)
            
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print("Successfully updated the file.")
