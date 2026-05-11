# convMD (Web to Markdown Toolkit)

**convMD** は、WEB上の様々なソース（記事、SNSの投稿、動画、音声）やローカルのOfficeファイルを、Obsidian などのナレッジベースで扱いやすい **Markdown（.md）形式** に自動変換・保存する統合ツールキットです。

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

### 🎥 動画・音声 (Media & Audio)
- **YouTube**: 動画URLからの字幕（トランスクリプト）全抽出。
- **ローカル音声/動画ファイル (`.mp3`, `.m4a`, `.mp4` など)**: `faster-whisper` を用いたオフラインでの高精度な自動文字起こし（※要FFmpeg）。

### 📄 ローカルファイル・汎用抽出
- **Office / PDF文書**: Microsoft `markitdown` エンジンを利用した PowerPoint, Excel, Word 等からのテキスト・Markdown抽出。
- **一般的なWebサイト**: `Readability` 相当のアルゴリズムを用いた、汎用的なニュース・ブログの本文抽出。

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

### 音声文字起こし機能を利用する場合の注意点
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

**1. Zenn や Qiita の記事を取得**
```bash
uv run python -m convmd.cli https://zenn.dev/username/articles/slug
uv run python -m convmd.cli https://qiita.com/username/items/item_id
```

**2. YouTubeの文字起こしを取得**
```bash
uv run python -m convmd.cli https://youtu.be/xxxxxxxxxxx
```

**3. 音声ファイルから議事録（文字起こし）を作成**
```bash
uv run python -m convmd.cli ./meeting_record.m4a
```

**4. ローカルのPowerPointをMarkdown化**
```bash
uv run python -m convmd.cli ./presentation.pptx
```

### 出力先の変更
デフォルトでは、実行したディレクトリ配下の `output/` フォルダに保存されます。
出力先を変更したい場合は `--output-dir` オプションを使用するか、環境変数 `CONVMD_OUTPUT_DIR` を設定してください。

```bash
uv run python -m convmd.cli https://example.com --output-dir "C:/Users/username/Documents/Obsidian"
```

---

## 🏗 アーキテクチャと品質基準

このプロジェクトは `python-safe-coding` 規約に準拠し、以下の基準で実装されています。
- 厳格な型ヒント (Type Hints) の適用と `mypy` (strict) による検証
- `ruff` による高速な静的解析とフォーマット
- 環境非依存（Mac/Windows）のパス操作 (`pathlib.Path`)
- 安全で高速なHTTP通信 (`httpx`)
