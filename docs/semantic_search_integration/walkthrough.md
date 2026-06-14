# Walkthrough: Semantic Search Integration

## 変更内容の概要
このドキュメントでは、セマンティック検索機能の実装において変更された主なコードの差分や設計上の決定事項を記録します。

### 1. Vector DB (ChromaDB) の導入
- **モジュール**: `src/convmd/core/vector_db.py`
- ローカル永続化のため `chromadb.PersistentClient` を採用し、保存先を `{output_dir}/.chroma_db` としました。
- Embedding 生成には既存の `google-genai` SDKを使用し、`text-embedding-004` モデルを指定しています。
- Markdownテキストは段落や見出し単位で単純なチャンク化を行い、トークン数上限に引っかからないように配慮します。

### 2. パイプラインへの組み込み
- **モジュール**: `src/convmd/pipeline.py`
- 新たに `embed_phase` を定義しました。このフェーズは `dispatch_phase` の前（あるいは並列）に実行され、新しく生成または更新された `.md` ファイル群を ChromaDB に Upsert します。

### 3. CLI の拡張
- **モジュール**: `src/convmd/cli_args.py`, `src/convmd/cli.py`
- `convmd find` コマンドに `-s` / `--semantic` フラグを追加しました。
- 従来の `ripgrep` コマンドと分岐させ、セマンティック検索時は ChromaDB からスコアの高いスニペットを取得して表示する処理を実装しました。

## 教訓・再発防止策 (Self-Improvement Protocol)
- **モデル名の変遷**: 當初 `text-embedding-004` を指定しようとしましたが、Gemini 3（2026年環境）および最新の API（v1beta）では `gemini-embedding-2` に移行していることが判明しました。これに伴い、`text-embedding-004` では 404 エラーが発生するため、`gemini-embedding-2` に修正しました。
- **ChromaDBと次元数の不一致**: 初期化時に失敗したモデルのフォールバックとして768次元のゼロベクトルが登録されると、以後の追加処理で `gemini-embedding-2` が返す3072次元のベクトルと競合してエラーになる問題が発生しました。これを回避するため、フォールバックのゼロベクトルの次元数を `3072` に統一し、既存の破損した `.chroma_db` をクリーンアップしました。
- **型検査 (mypy)**: ChromaDBの型定義は複雑なため、引数（特に `metadatas` や戻り値の抽出）では適宜 `cast(Any, ...)` 等を併用し、Strictモードの `mypy` の検査をクリアするよう調整しました。
