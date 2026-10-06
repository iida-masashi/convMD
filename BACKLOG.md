# BACKLOG

未着手の改善候補。着手時は前提（バージョン・料金・API仕様）を再確認すること。

## 依存パッケージ

- [ ] **firecrawl-anydoc の `<0.2` 固定解除**: 0.2.0〜0.2.4 は和暦書式（`[$-411]ge.m.d`）の Excel 日付セルをシリアル値（`1953-11-19` → `19682`）で出力する。新版が出たら `uv run pytest tests/test_office.py -k excel_dates` を新版で実行し、通れば固定を外す。
- [ ] **markitdown の `<0.1.6` 固定解除**: 0.1.6〜0.1.8 は縦書き PDF の読み順を崩す（例: `output/279_part5_raw.pdf` で「違反で結社禁止処分」が横方向に並び替わる）。新版で縦書き PDF の本文が正しくつながるか確認してから固定を外す。extras は `[all]` に戻さない（`youtube-transcript-api<1.1` に縛られ、字幕取得が空応答で失敗する）。

## Gemini

- [ ] **`gemini-3.1-pro-preview` の料金表が古い**: `pipeline._PRICE_USD_PER_1M_TOKENS` は (1.25, 5.00) だが、公式は入力 $2.00 / 出力 $12.00（プロンプト ≤200k tokens）、$4.00 / $18.00（>200k）。
- [ ] **`gemini-3.8-flash` の値上げ反映（2027-01-01）**: 入力 $0.75 → $1.50、出力 $3.75 → $7.50（1M tokens あたり）。
- [ ] **`gemini-3.8-flash` の思考トークン**: 既定で MEDIUM 思考が有効なため、短い OCR / 抽出でも出力トークンが膨らむ（2回の呼び出しで出力約1,000 tokens）。OCR・抽出に `thinking_level="low"` を指定するか検討（`MINIMAL` は 3.8-flash では 400 エラー）。
- [ ] **google-genai 2.28 の AFC 警告**: `generate_content` 呼び出し時に「Direct use of automatic function calling (AFC) ... is not recommended」が出る（2.17 では出ない）。動作に影響はない。抑止するなら `automatic_function_calling` を無効化する設定を渡す。
