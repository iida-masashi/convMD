#!/bin/bash
BASE="/Users/masashi/Documents/Obsidian Vault/理論・研究/03_氏族・系譜"
CLAN_DIR="$BASE/各氏族の研究"

# Create subdirectories
mkdir -p "$CLAN_DIR/忌部氏"
mkdir -p "$CLAN_DIR/海人族"
mkdir -p "$CLAN_DIR/阿波君・粟国造・長国造"
mkdir -p "$CLAN_DIR/出雲勢力"
mkdir -p "$CLAN_DIR/中臣氏"
mkdir -p "$CLAN_DIR/蘇我氏"
mkdir -p "$CLAN_DIR/物部氏"
mkdir -p "$CLAN_DIR/多氏"

# Move files based on wildcards
mv "$CLAN_DIR"/*忌部* "$CLAN_DIR/忌部氏/" 2>/dev/null
mv "$CLAN_DIR"/*天日鷲* "$CLAN_DIR/忌部氏/" 2>/dev/null
mv "$CLAN_DIR"/*種穂山* "$CLAN_DIR/忌部氏/" 2>/dev/null

mv "$CLAN_DIR"/*海人族* "$CLAN_DIR/海人族/" 2>/dev/null
mv "$CLAN_DIR"/*宇豆毘古* "$CLAN_DIR/海人族/" 2>/dev/null
mv "$CLAN_DIR"/*海洋祭祀* "$CLAN_DIR/海人族/" 2>/dev/null

mv "$CLAN_DIR"/*阿波君* "$CLAN_DIR/阿波君・粟国造・長国造/" 2>/dev/null
mv "$CLAN_DIR"/*鷲住王* "$CLAN_DIR/阿波君・粟国造・長国造/" 2>/dev/null
mv "$CLAN_DIR"/*粟国* "$CLAN_DIR/阿波君・粟国造・長国造/" 2>/dev/null
mv "$CLAN_DIR"/*長国* "$CLAN_DIR/阿波君・粟国造・長国造/" 2>/dev/null
mv "$CLAN_DIR"/*粟飯原氏* "$CLAN_DIR/阿波君・粟国造・長国造/" 2>/dev/null

mv "$CLAN_DIR"/*出雲* "$CLAN_DIR/出雲勢力/" 2>/dev/null
mv "$CLAN_DIR"/*国譲り* "$CLAN_DIR/出雲勢力/" 2>/dev/null
mv "$CLAN_DIR"/*伊津面* "$CLAN_DIR/出雲勢力/" 2>/dev/null

mv "$CLAN_DIR"/*中臣氏* "$CLAN_DIR/中臣氏/" 2>/dev/null

mv "$CLAN_DIR"/*蘇我氏* "$CLAN_DIR/蘇我氏/" 2>/dev/null

mv "$CLAN_DIR"/*物部氏* "$CLAN_DIR/物部氏/" 2>/dev/null

mv "$CLAN_DIR"/*多氏* "$CLAN_DIR/多氏/" 2>/dev/null

# Move foreign/immigrant related to the new root folder
mv "$CLAN_DIR"/*秦氏* "$BASE/渡来人と海外伝承/" 2>/dev/null
mv "$CLAN_DIR"/*徐福* "$BASE/渡来人と海外伝承/" 2>/dev/null
mv "$CLAN_DIR"/*イスラエル* "$BASE/渡来人と海外伝承/" 2>/dev/null
mv "$CLAN_DIR"/*渡来人* "$BASE/渡来人と海外伝承/" 2>/dev/null
mv "$CLAN_DIR"/*東夷王* "$BASE/渡来人と海外伝承/" 2>/dev/null

echo "Organization complete."
