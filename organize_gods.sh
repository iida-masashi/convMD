#!/bin/bash
BASE="/Users/masashi/Documents/Obsidian Vault/理論・研究/03_氏族・系譜"
GODS_DIR="$BASE/神々の系譜"

# Move out mismatched files
mv "$GODS_DIR/安房・阿波に関わる天皇一覧.md" "$BASE/歴代天皇と伝承/" 2>/dev/null
mv "$GODS_DIR/阿波の出雲トポグラフィー：伊津面から読み解く国譲りの真実.md" "$BASE/各氏族の研究/出雲勢力/" 2>/dev/null

mkdir -p "$BASE/大嘗祭と皇室祭祀"
mv "$GODS_DIR/"*大嘗祭* "$BASE/大嘗祭と皇室祭祀/" 2>/dev/null

# Create god specific folders
mkdir -p "$GODS_DIR/大宜都比売命（オオゲツヒメ）"
mkdir -p "$GODS_DIR/大国主命・大己貴神"
mkdir -p "$GODS_DIR/事代主命（エビス）"
mkdir -p "$GODS_DIR/天照大神（アマテラス）"
mkdir -p "$GODS_DIR/天火明命（アメノホアカリ）"

# Move files
mv "$GODS_DIR"/*大宜都比売* "$GODS_DIR/大宜都比売命（オオゲツヒメ）/" 2>/dev/null
mv "$GODS_DIR"/*大国主* "$GODS_DIR/大国主命・大己貴神/" 2>/dev/null
mv "$GODS_DIR"/*大己貴神* "$GODS_DIR/大国主命・大己貴神/" 2>/dev/null
mv "$GODS_DIR"/*事代主* "$GODS_DIR/事代主命（エビス）/" 2>/dev/null
mv "$GODS_DIR"/*天照大神* "$GODS_DIR/天照大神（アマテラス）/" 2>/dev/null
mv "$GODS_DIR"/*天火明命* "$GODS_DIR/天火明命（アメノホアカリ）/" 2>/dev/null

mkdir -p "$GODS_DIR/重要な神社・祭祀"
mv "$GODS_DIR"/*王ケ原神宮* "$GODS_DIR/重要な神社・祭祀/" 2>/dev/null
mv "$GODS_DIR"/*大御和神社* "$GODS_DIR/重要な神社・祭祀/" 2>/dev/null

echo "Gods organization complete."
