# Implementation Plan: Obsidian Enhancements

## フェーズ 1: フロントマター生成ロジックの強化
- [Step 1] -> verify: `generate_frontmatter`（`src/convmd/core/utils.py`）を、`tags`/`aliases` を YAML 配列で出力し、`created_at` を ISO-8601 形式にするよう拡張する。
- [Step 2] -> verify: `tests/test_utils.py` にフロントマター形式の検証テストを追加し、`uv run pytest` で確認する。

## フェーズ 2: 自動Wikiリンクとタグ付けの強化（AI活用）
- [Step 3] -> verify: `apply_obsidian_links`（`src/convmd/core/transform.py`）のプロンプトを厳密化し、「本文の改行・見出し・画像リンク・フロントマターを変更しない」ことを強く指示する。
- [Step 4] -> verify: AI が出力した末尾の `TAGS: タグ1, タグ2` 行を解析・除去し、抽出したタグをフロントマターの `tags` 配列へ挿入するロジックを実装する。
- [Step 5] -> verify: `tests/test_transform.py` に `apply_obsidian_links` のテストを追加する。

## フェーズ 3: Obsidian Local REST API 連携
- [Step 6] -> verify: `src/convmd/integrations/obsidian_rest.py` に `export_to_obsidian_api(file_path, api_url, token, target_folder)` を実装する。`httpx` で `PUT /vault/{folder}/{filename}` にコンテンツを送信し、成功/失敗を bool で返す。
- [Step 7] -> verify: `pipeline.py` の後処理フェーズに組み込み、`OBSIDIAN_REST_API_URL` / `OBSIDIAN_REST_API_KEY` の両方が設定されている場合のみ実行するようにする（未設定・失敗時は通常の `output/` 保存のみで処理を継続）。
- [Step 8] -> verify: `tests/test_obsidian_rest.py` で成功・失敗系のテストを追加する。
