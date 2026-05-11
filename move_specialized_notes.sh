#!/bin/bash
VAULT="/Users/masashi/Documents/Obsidian Vault"
ARCHIVE="$VAULT/資料/Web_Archives"
THEORY="$VAULT/理論・研究"

echo "Moving 古史古伝_専門ノート..."
mv "$ARCHIVE/古史古伝_専門ノート" "$THEORY/04_神話・古典解読/" 2>/dev/null

echo "Moving 神代文字_専門ノート..."
mv "$ARCHIVE/神代文字_専門ノート" "$THEORY/04_神話・古典解読/" 2>/dev/null

echo "Moving 古典文学_専門ノート..."
mv "$ARCHIVE/古典文学_専門ノート" "$THEORY/04_神話・古典解読/" 2>/dev/null

echo "Moving 阿波説の根幹_専門ノート..."
mv "$ARCHIVE/阿波説の根幹_専門ノート" "$THEORY/01_理論基盤・総論/阿波説の核心/" 2>/dev/null

echo "Moving 徐福伝説_専門ノート..."
mv "$ARCHIVE/徐福伝説_専門ノート" "$THEORY/03_氏族・系譜/渡来人と海外伝承/" 2>/dev/null

echo "Moving 都市伝説_ミステリー..."
mv "$ARCHIVE/都市伝説_ミステリー" "$THEORY/06_信仰・霊性/" 2>/dev/null

echo "Moving その他_専門ノート..."
# 既にフォルダがある場合は中身を移動
if [ -d "$ARCHIVE/その他_専門ノート" ]; then
    cp -r "$ARCHIVE/その他_専門ノート/"* "$THEORY/01_理論基盤・総論/その他_詳細論点/" 2>/dev/null
    rm -rf "$ARCHIVE/その他_専門ノート"
fi

echo "Move operations completed."
