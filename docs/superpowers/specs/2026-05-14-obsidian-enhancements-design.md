# Obsidian Enhancements Design

## 1. プロパティ（YAML Frontmatter）の強化

**目的**: Obsidianの最新の「プロパティUI」に完全に準拠したメタデータを出力する。

**設計**:
`src/convmd/core/utils.py` の `generate_frontmatter` 関数を拡張する。
*   `tags`: 単なるカンマ区切り文字列ではなく、YAMLの配列（リスト）形式で出力する。
*   `aliases`: タイトルの短縮形などを格納するリストプロパティを追加。
*   `created_at`, `updated_at`: Obsidianでソート可能な ISO-8601 フォーマットを適用。
*   カスタムメタデータ（`extra` 引数）を階層構造で出力し、ソース元固有の情報を整理する。

## 2. 自動Wikiリンクとタグ付けの強化（AI活用）

**目的**: 本文の構造を壊さずに、重要なキーワードをWikiリンク（`[[ ]]`）化し、適切なタグを生成する。

**設計**:
`src/convmd/core/transform.py` の `_AUTO_LINK_INSTRUCTION` を改修する。
*   プロンプトの厳密化: 「本文の内容、改行、見出し、画像リンクを一切変更しないこと」を強く指示。
*   リンク置換: 重要な名詞のみを `[[名詞]]` に置換する。必要に応じて `[[正式名称|表示名]]` 形式を使用する。
*   タグ抽出: プロンプト内で「タグはファイルの末尾にカンマ区切りのプレーンテキスト（例: `TAGS: 歴史, 仏教`）として出力せよ」と指示する。
*   後処理: Pythonコード側で生成されたテキストの末尾から `TAGS: ...` を解析・削除し、抽出したタグを1のFrontmatterの `tags` 配列に挿入してからファイルに書き込む。

## 3. Obsidian Local REST API 連携

**目的**: ファイルをローカルの `output/` に保存するだけでなく、ObsidianのVault内に直接インポートする。

**設計**:
`src/convmd/integrations/obsidian.py` を大幅に強化し、エクスポート機能を追加する。
*   **要件**: Obsidianの「Local REST API」プラグインが起動していること。
*   **設定**: `.env` ファイル、または環境変数（`OBSIDIAN_REST_API_URL`、`OBSIDIAN_REST_API_KEY`）からAPIのURL（例: `https://127.0.0.1:27124`）とBearerトークンを読み込む。
*   **動作**: `convMD` のパイプラインの最終ステップで、Markdownが生成されたら `httpx` を使用して `PUT /vault/{folder}/{filename}.md` にコンテンツを送信する。
*   **フォールバック**: APIの設定がない、または通信に失敗した場合は、通常の `output/` フォルダへの保存のみを行う（処理を止めない）。
