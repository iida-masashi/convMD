#!/bin/bash
BASE="/Users/masashi/Documents/Obsidian Vault"
THEORY_BASE="$BASE/理論・研究"
CORE_DIR="$THEORY_BASE/01_理論基盤・総論/阿波説の核心"
AWA_NOTES_DIR="$CORE_DIR/阿波説の根幹_専門ノート"

# 1. 既存の専門ノートへ統合（移動）
# 邪馬台国・若杉山関連 -> 「阿波の考古学的先行性_詳細」または「古代阿波の資源独占と経済基盤_詳細」などへ
mv "$AWA_NOTES_DIR/若杉山辰砂採掘遺跡_魏志倭人伝の「丹」の供給源.md" "$CORE_DIR/古代阿波の資源独占と経済基盤_詳細/" 2>/dev/null
mv "$AWA_NOTES_DIR/邪馬台国阿波説_水行十日陸行一月の真のルート.md" "$THEORY_BASE/05_地理・地政学/" 2>/dev/null

# 神山町・高天原 -> 記紀神話の舞台移動論_詳細
mv "$AWA_NOTES_DIR/高天原の実在証明_徳島県神山町と延喜式内社の密集.md" "$CORE_DIR/記紀神話の舞台移動論_詳細/" 2>/dev/null

# 剣山・天孫降臨 -> 信仰・霊性 または 地名ペア検証
mv "$AWA_NOTES_DIR/剣山（鶴亀山）と天孫降臨_古代山岳信仰の聖地.md" "$THEORY_BASE/06_信仰・霊性/阿波の古刹・霊場伝承/" 2>/dev/null

# 神武東征 -> 05_地理・地政学
mv "$AWA_NOTES_DIR/神武東征の出発地は日向（宮崎）ではなく南阿波説.md" "$THEORY_BASE/05_地理・地政学/" 2>/dev/null

# 阿波忌部・産業 -> 03_氏族・系譜/各氏族の研究/忌部氏
mv "$AWA_NOTES_DIR/阿波忌部氏の歴史と産業_麻・穀・紙が支えた古代王権.md" "$THEORY_BASE/03_氏族・系譜/各氏族の研究/忌部氏/" 2>/dev/null

# 大嘗祭と麁服 -> 03_氏族・系譜/大嘗祭と皇室祭祀
mv "$AWA_NOTES_DIR/大嘗祭と麁服（あらたえ）_天皇即位に必須の阿波の神布.md" "$THEORY_BASE/03_氏族・系譜/大嘗祭と皇室祭祀/" 2>/dev/null

# 概論 -> 01_理論基盤・総論 の直下か阿波説の核心へ
mv "$AWA_NOTES_DIR/阿波説の概論_なぜ徳島が日本の起源とされるのか.md" "$CORE_DIR/" 2>/dev/null

# 2. 空になったフォルダを削除
rmdir "$AWA_NOTES_DIR" 2>/dev/null
rm -rf "$BASE/資料/Web_Archives/阿波説の根幹_専門ノート" 2>/dev/null

echo "Awa theory notes integrated into the broader structure."
