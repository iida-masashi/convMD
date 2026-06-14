# Semantic Search Integration Task

## 概要 (Overview)
`convMD` の検索機能 (`convmd find`) に、Gemini の Embedding モデル (`text-embedding-004`) と ChromaDB を用いたセマンティック検索（意味検索）モードを追加する。
従来の `ripgrep` によるキーワード一致だけでなく、「類似する概念」でノートを検索可能にし、ナレッジベースとしての価値を向上させる。

## 目的 (Objectives)
- `google-genai` を用いたドキュメントのベクトル化 (Embedding) 機能の実装。
- ChromaDB をローカルベクトルDBとして組み込み、Markdownファイルのチャンクを永続化する。
- 抽出・変換パイプライン (`pipeline.py`) に、結果をベクトルDBへUpsertする `embed_phase` を追加。
- `convmd find` コマンドに `--semantic` フラグを追加し、ベクトル検索を実行できるようにする。

## ステータス (Status)
- [x] ドキュメント作成
- [x] 依存パッケージ (`chromadb`) の追加
- [x] `core/vector_db.py` の実装
- [x] `pipeline.py` への組み込み
- [x] `cli.py` / `cli_args.py` への検索機能組み込み
- [x] 検証 (Lint, Type Check, 動作確認)
