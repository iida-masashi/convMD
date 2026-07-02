# Walkthrough: Obsidian Enhancements

## 変更内容の概要
このドキュメントでは、Obsidian連携機能の実装において変更された主なコードの差分や設計上の決定事項を記録します。

### 1. フロントマター生成の強化
- **モジュール**: `src/convmd/core/utils.py`
- `generate_frontmatter(title, url, tags=..., *, extra=..., author=..., published_at=..., reading_time_min=..., excerpt=..., cover=...)` — `tags`/`aliases` は YAML 配列形式、`created_at` は ISO-8601（UTC）で出力する。
- 計画段階の引数名 `source_url` は、実装時に他の呼び出し箇所との一貫性のため `url` に変更されている。

### 2. 自動Wikiリンクとタグ付け
- **モジュール**: `src/convmd/core/transform.py`
- `apply_obsidian_links` は Gemini に本文中の重要語を `[[wikilink]]` 化させ、末尾の `TAGS: ...` 行からタグを抽出してフロントマターの `tags` 配列に追記する。
- プロンプトでは「本文の意味・改行・見出し・画像リンク・フロントマターを変更しない」ことを明示し、AIによる意図しない改変を防止している。

### 3. Obsidian Local REST API 連携
- **モジュール**: `src/convmd/integrations/obsidian_rest.py`
- `export_to_obsidian_api(file_path, api_url, token, target_folder="Inbox")` が `httpx.Client` で `PUT /vault/{folder}/{filename}` を送信する。
- Local REST API はセルフ署名証明書が一般的なため、`verify=False` を明示的に指定している（`core/http.py` の集中管理からは意図的に外れる例外）。
- `pipeline.py` の `dispatch_phase` で `OBSIDIAN_REST_API_URL` / `OBSIDIAN_REST_API_KEY` の両方が環境変数に設定されている場合のみ呼び出される。未設定・通信失敗時は通常の `output/` 保存のみで処理を継続し、パイプライン全体は止めない。

## 現状
上記3機能はすべて実装済み。同じパターン（環境変数ゲート＋`dispatch_phase` からの呼び出し）は、後発の Notion 連携（`docs/`には未整理、`src/convmd/integrations/notion.py`）でも踏襲されている。
