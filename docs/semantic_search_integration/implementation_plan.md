# Implementation Plan: Semantic Search

## フェーズ 1: 環境構築
- [Step 1] -> verify: `uv add chromadb` を実行し、`pyproject.toml` に依存関係を追加する。
- [Step 2] -> verify: 必要な型定義等があれば追加し、`uv sync` で環境を最新化する。

## フェーズ 2: Vector DB モジュール実装 (`src/convmd/core/vector_db.py`)
- [Step 3] -> verify: `chromadb` を初期化し、`output_dir/.chroma_db` に永続化する `ChromaManager` クラスを実装する。
- [Step 4] -> verify: `core/gemini.py` または独自に `google-genai` の `embed_content` を呼び出すラッパーを実装。
- [Step 5] -> verify: Markdownファイルを適度なサイズにチャンク化し、メタデータ（ファイルパス、タイトルなど）と共に ChromaDB に Upsert するメソッドを実装。
- [Step 6] -> verify: クエリ文字列を受け取り、ベクトル化して ChromaDB から近似近傍検索を行う `search` メソッドを実装。

## フェーズ 3: パイプライン統合 (`src/convmd/pipeline.py`)
- [Step 7] -> verify: `pipeline.py` に `embed_phase(files, cfg)` を追加する。
- [Step 8] -> verify: `diff_phase` 等を通過した（更新があった）ファイルのみを対象に、`ChromaManager` を用いてUpsertを実行するよう `run_pipeline` / `run_once` に組み込む。

## フェーズ 4: CLIコマンド拡張 (`src/convmd/cli.py`, `src/convmd/cli_args.py`)
- [Step 9] -> verify: `cli_args.py` の `build_find_parser` に `--semantic` (または `-s`) フラグを追加する。
- [Step 10] -> verify: `cli.py` の `_handle_find` 関数を修正し、`--semantic` が指定された場合は `vector_db.py` の検索を呼び出し、結果をフォーマットして出力するようにする。

## フェーズ 5: テストと型検査
- [Step 11] -> verify: `uv run ruff check .` および `uv run mypy src` を実行し、静的解析エラーを修正する。
- [Step 12] -> verify: 実際に任意のURLを変換し、その後 `convmd find "query" --semantic` で結果が返るか動作確認を行う。
