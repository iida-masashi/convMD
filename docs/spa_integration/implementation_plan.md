# Implementation Plan: SPA Integration

## フェーズ 1: パッケージと環境の更新
- [Step 1] -> verify: `uv add playwright` を実行し、`pyproject.toml` に追加。
- [Step 2] -> verify: `uv add --dev pytest pytest-asyncio` を実行してテストフレームワークを最新化。
- [Step 3] -> verify: `uv run playwright install chromium` を実行し、必要なブラウザバイナリをインストールする。

## フェーズ 2: CLIと設定の拡張
- [Step 4] -> verify: `src/convmd/cli_args.py` の `build_parser` および `to_run_config` に `--render-js` (bool) フラグを追加する。

## フェーズ 3: HTTPモジュールの拡張 (`src/convmd/core/http.py`)
- [Step 5] -> verify: `http.py` に `get_html(url, render_js=False)` のようにオプショナルで Playwright を呼び出すか、別関数 `get_html_with_js(url)` を追加する。
- [Step 6] -> verify: Playwright (sync API) を使用して、ページ読み込み後にHTMLのコンテンツを返す処理を実装する。

## フェーズ 4: パーサーへの適用
- [Step 7] -> verify: `routing.py` のフォールバックロジックや、`general.py` (Readability適用前) において、`cfg.render_js` が True の場合は JS レンダリング済みのHTMLを取得するようにコードを修正する。

## フェーズ 5: テストと静的解析の実行
- [Step 8] -> verify: `uv run ruff check --fix .` および `uv run mypy src` を実行。
- [Step 9] -> verify: `uv run pytest` を実行し、既存のテストが壊れていないか、パスするかを確認する。
