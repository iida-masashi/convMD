# Web to Markdown Toolkit

WEB上の様々なソース（note.com, X/Twitter, 静的サイトなど）をMarkdownファイルに変換するためのツール集です。

## ディレクトリ構造
- `main.py`: メインの実行プログラム。入力されたURLやファイルパスから適切な変換ツールを自動選択します。
- `note_converter.py`: note.com の記事一覧や本文を取得します。
- `twitter_converter.py`: X (Twitter) の最新の投稿を取得します。
- `kojiki_converter.py`: 特殊な構造の静的サイト（阿波と古事記など）を解析します。
- `general_converter.py`: 一般的なWEBページを汎用的にMarkdownへ変換します。
- `office_converter.py`: Microsoftの「MarkItDown」を利用して、ローカルのPowerPoint、Excel、Word、PDFなどをMarkdownに変換します。※注意: この機能の利用にはPython 3.10以上と `markitdown` ライブラリのインストールが必要です。

## 使い方
ターミナルから以下のコマンドを実行してください。

```bash
python3 web_to_md_tool/main.py <対象のURL または ファイルパス>
```

### 例
1. **note.com の全記事を取得する場合**
   ```bash
   python3 web_to_md_tool/main.py https://note.com/cute_hebe442
   ```

2. **X (Twitter) の投稿を取得する場合**
   ```bash
   python3 web_to_md_tool/main.py https://x.com/kamiyamafudoki
   ```

3. **一般的なニュース記事やブログを1件変換する場合**
   ```bash
   python3 web_to_md_tool/main.py https://kamakura8.blogspot.com/2021/08/blog-post_13.html
   ```

4. **ローカルのPowerPointやExcelファイルを変換する場合 (MarkItDown使用)**
   ```bash
   python3 web_to_md_tool/main.py ./presentation.pptx
   ```

## 保存先
- noteの記事は `note_posts/` フォルダへ
- Xの投稿は `note_posts/` フォルダへ（ファイル名: `ユーザー名_tweets.md`）
- Kojikiサイトは `kojiki_md/` フォルダへ
- 一般的なサイトは `misc_posts/` フォルダへ
それぞれ保存されます。
