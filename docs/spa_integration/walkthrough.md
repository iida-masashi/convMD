# Walkthrough: SPA Integration & Pytest Update

## 変更内容の概要
Playwright を用いた JavaScript レンダリング（SPA対応）を実装し、テストフレームワークの最新化を完了しました。

### 1. Playwright の導入と `core/http.py` 拡張
- `uv add playwright` で依存関係を追加し、Chromium をインストールしました。
- `core/http.py` に `get_html_with_js` を追加し、`sync_playwright` を使用して JS を完全に実行した後の DOM を取得する機能を実装しました。
- 既存の `get_html` に `render_js` (bool) パラメータを追加し、True の場合は Playwright にフォールバックするよう統合しました。

### 2. CLIとルーティングの更新
- `cli_args.py` に `--render-js` フラグを追加し、`RunConfig` に引き回せるようにしました。
- `core/download.py` の `fetch_html`、および `parsers/general.py` の `convert_general_website` も `render_js` を受け取るように拡張しました。
- `routing.py` の汎用サイト抽出フォールバック、および失敗時/短文時のAIフォールバック抽出 (`extract_with_llm`) において、ユーザーが指定した `--render-js` フラグが正しく伝搬されるように修正しました。

### 3. テストの最新化
- `uv add --dev pytest pytest-asyncio` を実行して Pytest を更新しました。
- `uv run ruff check --fix .` および `uv run mypy src` にて静的解析をパスすることを確認しました。
- `uv run pytest` を実行し、全191件のテストが通過 (PASS) することを証明しました。

## 教訓・再発防止策 (Self-Improvement Protocol)
- `RunConfig` データクラスを拡張した際、`cli_args.py` の末尾のカッコでシンタックスエラーを一時的に起こしましたが、即座に修正・型チェックで拾い上げました。変更を加える際は、対応する Dataclass のフィールドと argparse の両方を漏れなく更新することが重要です。
