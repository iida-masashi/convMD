# convMD (Web to Markdown Toolkit)

**convMD** は、WEB上の様々なソース（記事、SNSの投稿、動画、音声、デジタルアーカイブ）やローカルのOfficeファイルを、Obsidian などのナレッジベースで扱いやすい **Markdown（.md）形式** に自動変換・保存する統合ツールキットです。

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![uv](https://img.shields.io/badge/package%20manager-uv-magenta.svg)

## 🚀 主な機能と対応プラットフォーム

URLやファイルパスを引数に渡すだけで、システムが自動的にプラットフォームを判別し、最適な変換エンジンを適用します。

### 📱 SNS・メディア (Web sources)
- **Zenn (`zenn.dev`)**: 記事のMarkdown抽出。
- **Qiita (`qiita.com`)**: 記事本文の抽出、およびユーザーごとの最新記事一括取得。
- **note (`note.com`)**: クリエイターの最新記事一覧の一括取得。
- **X / Twitter (`x.com`)**: ユーザーのタイムライン取得（画像含む）とスレッドのMarkdown化。
- **Wikipedia (`wikipedia.org`)**: ナビゲーション等を除去したクリーンな本文抽出（他言語対応）。

### 🏛️ デジタルアーカイブ・画像文字起こし (IIIF & OCR)
- **国書データベース (`kokusho.nijl.ac.jp`)**: 古典籍の書誌データ抽出と、IIIFマニフェストからの高画質画像の自動ダウンロード。
- **AIによる古文書OCR**: ダウンロードした画像に対し、最新の Gemini API (`gemini-3.1-pro-preview` / `gemini-3-flash-preview`) を用いた高精度な文字起こし（翻刻）を自動で実行し、Markdownに追記します。

### 🎥 動画・音声 (Media & Audio)
- **YouTube**: 動画URLからの字幕（トランスクリプト）全抽出。
- **ローカル音声/動画ファイル (`.mp3`, `.m4a`, `.mp4` など)**: `faster-whisper` を用いたオフラインでの高精度な自動文字起こし（※要FFmpeg）。

### 📄 ローカルファイル・汎用抽出
- **Office / PDF文書**: Microsoft `markitdown` エンジンを利用した PowerPoint, Excel, Word 等からのテキスト・Markdown抽出。
- **一般的なWebサイト**: `Readability` 相当のアルゴリズムを用いた、汎用的なニュース・ブログの本文抽出。

### ✨ AIトランスフォーム機能 (Transformation)
- 生成されたMarkdownファイルに対して、任意の指示（例：「現代語訳して」「要点を3つにまとめて」）を与え、Gemini API を使って内容を自動変換する `--transform` 機能を搭載しています。

---

## 🛠 インストール方法

モダンなPythonパッケージマネージャーである **[uv](https://docs.astral.sh/uv/)** の利用を推奨しています。

```bash
# リポジトリのクローン
git clone https://github.com/iida-masashi/convMD.git
cd convMD

# uv を用いた依存関係の同期（仮想環境の自動作成）
uv sync
```

### 必要な環境変数・外部ツール
一部の高度な機能を利用するためには、以下のセットアップが必要です。

- **AI連携機能（OCR, トランスフォーム）**:
  Gemini API を利用するため、環境変数にAPIキーを設定してください。
  ```powershell
  # Windows PowerShellの場合
  $env:GOOGLE_API_KEY="your_api_key_here"
  # または GEMINI_API_KEY でも可
  ```

- **音声文字起こし機能**:
  ローカル音声ファイルの文字起こし（`faster-whisper`）を利用する場合は、システムに **FFmpeg** がインストールされている必要があります。
  - **Windows (winget)**: `winget install ffmpeg`
  - **macOS (Homebrew)**: `brew install ffmpeg`

---

## 💻 使い方

`uv run python -m convmd.cli` コマンドの後に、変換したいターゲットの URL または ファイルパス を指定します。

### 基本コマンド
```bash
uv run python -m convmd.cli <対象のURL または ファイルパス>
```

### 実行例

**1. デジタルアーカイブ（国書データベース）の取得**
```bash
uv run python -m convmd.cli https://kokusho.nijl.ac.jp/biblio/100243699/
# (APIキーが設定されていれば、全画像のダウンロードと同時に漢文の自動文字起こしが行われます)
```

**2. Zenn や Qiita の記事を取得**
```bash
uv run python -m convmd.cli https://zenn.dev/username/articles/slug
```

**3. YouTubeの文字起こしを取得**
```bash
uv run python -m convmd.cli https://youtu.be/xxxxxxxxxxx
```

**4. 音声ファイルから議事録を作成**
```bash
uv run python -m convmd.cli ./meeting_record.m4a
```

### 出力先の変更
デフォルトでは、実行したディレクトリ配下の `output/` フォルダに保存されます。
出力先を変更したい場合は `--output-dir` オプションを使用するか、環境変数 `CONVMD_OUTPUT_DIR` を設定してください。

```bash
uv run python -m convmd.cli https://example.com --output-dir "C:/Users/username/Documents/Obsidian"
```

### AIトランスフォーム（変換）機能
ローカルのMarkdownファイルを指定し、`--transform` オプションに指示を渡すことで、AIによるテキストの加工（現代語訳、要約など）が可能です。

```bash
uv run python -m convmd.cli ./output/article.md --transform "要点を箇条書きで3つにまとめてください"
```
（※結果は `article_transformed.md` として保存されます）

---

## 🏗 アーキテクチャと品質基準

このプロジェクトは `python-safe-coding` 規約に準拠し、以下の基準で実装されています。
- 厳格な型ヒント (Type Hints) の適用と `mypy` (strict) による検証
- `ruff` による高速な静的解析とフォーマット
- 環境非依存（Mac/Windows）のパス操作 (`pathlib.Path`)
- 安全で高速なHTTP通信 (`httpx`)
- スケーラブルで再利用性の高いモジュール構成（旧 `legacy/` スクリプトの廃止）
