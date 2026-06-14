# SPA (Playwright) Integration & Pytest Update Task

## 概要 (Overview)
`convMD` のウェブ抽出機能に、JavaScriptレンダリングが必要なSPA（Single Page Application）サイトに対応するため、Playwright 統合を追加する。
また、既存のテストフレームワーク（Pytest）を最新化し、テストカバレッジと健全性を維持する。

## 目的 (Objectives)
- 依存パッケージとして `playwright` を追加。
- `core/http.py` に、Playwrightを用いたDOM取得関数 (`get_html_with_js`) を実装。
- CLIオプションに `--render-js` を追加し、ユーザーがSPA抽出モードを指定できるようにする。
- 動的ルーティング (`routing.py`) のAIフォールバック等で必要に応じて JS レンダリング版 HTML を利用するように調整（または設定を渡す）。
- Pytest を最新化し、ローカルで全テストを実行・PASSさせる。

## ステータス (Status)
- [x] ドキュメント作成
- [x] 依存パッケージ (`playwright`, `pytest` 等の最新化) の追加・同期
- [x] `core/http.py` への Playwright 統合
- [x] `cli_args.py` への `--render-js` 追加
- [x] `routing.py` / `parsers/general.py` 等への設定反映
- [x] テストの実行 (pytest)
