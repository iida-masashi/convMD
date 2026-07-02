# Obsidian Enhancements Task

## 概要 (Overview)
`convMD` を強化し、Obsidian 向けの厳密な YAML フロントマター出力、AI による Wikiリンク置換・タグ生成、および Local REST API 経由での Vault への直接インポート機能を追加する。

## 目的 (Objectives)
- `generate_frontmatter` を拡張し、Obsidian の「プロパティUI」に完全準拠したメタデータ（配列形式の `tags`/`aliases`、ISO-8601 の `created_at` 等）を出力する。
- `apply_obsidian_links` で本文の構造を壊さずに重要キーワードを `[[wikilink]]` 化し、AI が生成したタグをフロントマターへ自動挿入する。
- Obsidian の Local REST API プラグイン経由で、生成した Markdown を Vault 内へ直接書き込めるようにする（`OBSIDIAN_REST_API_URL` / `OBSIDIAN_REST_API_KEY`）。API 未設定・通信失敗時は通常の `output/` 保存にフォールバックし、処理を止めない。

## Tech Stack
Python 3.10+, httpx, Obsidian Local REST API, Gemini API
