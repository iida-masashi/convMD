#!/bin/bash
TARGET="/Users/masashi/Documents/Obsidian Vault/都市伝説と神秘伝承"
DEST_BASE="/Users/masashi/Documents/Obsidian Vault/理論・研究/06_信仰・霊性/都市伝説・偽書_専門ノート"

# 1. 剣山アークは陰謀論・ミステリーへ
mv "$TARGET/剣山と「失われたアーク」伝説.md" "$DEST_BASE/歴史_古史古伝_陰謀論/" 2>/dev/null

# 2. UFO・天磐船はオカルト・ミステリーへ
mv "$TARGET/UFOと「天磐船（あめのいわふね）」.md" "$DEST_BASE/歴史ミステリー_飛躍した仮説/" 2>/dev/null

# 3. 日月神示、ひふみ祝詞、言霊系は神代文字・オカルトへ（あるいはスピリチュアル）
mkdir -p "$DEST_BASE/スピリチュアル_予言・祝詞"
mv "$TARGET/"*ひふみ祝詞*.md "$DEST_BASE/スピリチュアル_予言・祝詞/" 2>/dev/null
mv "$TARGET/"*日月神示*.md "$DEST_BASE/スピリチュアル_予言・祝詞/" 2>/dev/null
mv "$TARGET/"*天之日津久神社*.md "$DEST_BASE/スピリチュアル_予言・祝詞/" 2>/dev/null
mv "$TARGET/降臨の経緯.md" "$DEST_BASE/スピリチュアル_予言・祝詞/" 2>/dev/null
mv "$TARGET/神示の内容と特色.md" "$DEST_BASE/スピリチュアル_予言・祝詞/" 2>/dev/null

# 4. 阿波の都市伝説まとめはそのままミステリー直下か専用フォルダへ
mkdir -p "$DEST_BASE/阿波のミステリー"
mv "$TARGET/阿波の都市伝説・奇談・神秘伝承.md" "$DEST_BASE/阿波のミステリー/" 2>/dev/null
mv "$TARGET/阿波説との交差.md" "$DEST_BASE/阿波のミステリー/" 2>/dev/null

# 5. 祟り伝承
mv "$TARGET/空位の神社と「祟り」の伝承.md" "$DEST_BASE/神社_呪術_霊的都市伝説/" 2>/dev/null

# 6. その他の細かなもの
mv "$TARGET/"*.md "$DEST_BASE/スピリチュアル_予言・祝詞/" 2>/dev/null

# もし都市伝説・偽書_専門ノートというフォルダが間違って作られていたらマージする
if [ -d "$TARGET/都市伝説・偽書_専門ノート" ]; then
    cp -r "$TARGET/都市伝説・偽書_専門ノート/"* "$DEST_BASE/" 2>/dev/null
    rm -rf "$TARGET/都市伝説・偽書_専門ノート"
fi

# 空になったら削除
rmdir "$TARGET" 2>/dev/null || echo "Directory not empty, could not delete."

echo "Mysteries organized."
