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
- **国立公文書館デジタルアーカイブ (`digital.archives.go.jp`)**: ビューワーURLからのIIIFマニフェスト自動解析、高画質画像のダウンロード、およびAI OCRによる翻刻。
- **GitHub (`github.com`)**: README / Issue / Pull Request 本文＋コメントを取得（`GITHUB_TOKEN` で認証可）。
- **Reddit (`reddit.com`)**: スレッド本文＋トップレベルコメント取得。
- **Hacker News (`news.ycombinator.com`)**: 投稿本文＋上位コメント階層の取得。
- **はてなブログ (`hatenablog.com` / `hatenablog.jp`)**, **Substack (`*.substack.com`)**, **Medium (`medium.com`)**: 本文抽出。
- **SpeakerDeck (`speakerdeck.com`)**: 全スライド画像のダウンロードと、Gemini OCRによる自動文字起こし。
- **Podcast / RSS (`*.rss`, `*.xml`, `/feed`)**: 最新エピソードのMP3を自動取得し、`faster-whisper` で文字起こし。

### 🏛️ デジタルアーカイブ・画像文字起こし (IIIF & OCR)
- **国書データベース (`kokusho.nijl.ac.jp`)**: 古典籍の書誌データ抽出と、IIIFマニフェストからの高画質画像の自動ダウンロード。
- **AIによる古文書OCR**: ダウンロードした画像に対し、最新の Gemini API (`gemini-3.1-pro-preview` / `gemini-3-flash-preview`) を用いた高精度な文字起こし（翻刻）を自動で実行し、Markdownに追記します。

### 🎥 動画・音声 (Media & Audio)
- **YouTube**: 動画URLからの字幕（トランスクリプト）全抽出。
- **ローカル音声/動画ファイル (`.mp3`, `.m4a`, `.mp4` など)**: `faster-whisper` を用いたオフラインでの高精度な自動文字起こし（※要FFmpeg）。

### 📄 ローカルファイル・汎用抽出
- **Office / PDF文書**: Microsoft `markitdown` エンジンを利用した PowerPoint, Excel, Word 等からのテキスト・Markdown抽出。
- **一般的なWebサイト**: `Readability` 相当のアルゴリズムを用いた、汎用的なニュース・ブログの本文抽出。

### ✨ ハイブリッド自律抽出エンジン (Hybrid Extraction)
- **Tier 1 (Static)**: `Readability` や専用パーサーによる高速・低コストな抽出。
- **Tier 2 (AI-Driven)**: 既存の解析が失敗した場合や、`--ai-extract` 指定時に、Gemini 3 がDOM構造を自律的に解析して Markdown 化します（本質的なコンテンツの抽出、メタデータの自動付与）。
- **カスタムスキーマ**: `--schema` オプションに JSON 形式で抽出したい項目を指定することで、特定の情報を構造化データとして引き出すことが可能です。
- **トランスフォーム**: 生成されたMarkdownファイルに対して、`--transform` オプションで任意の指示（例：「現代語訳して」「要約して」）を与え、Gemini API を使って内容を自動変換できます。
- `--auto-link` で重要キーワードを Obsidian の内部リンク `[[ ]]` に自動変換、`--summary` で複数ファイル横断のエグゼクティブサマリーを生成。

### 🔁 差分追跡・コスト可視化・全文検索 (Phase 3)
- 出力ディレクトリ配下に SQLite (`.convmd.db`) を持ち、URL ごとの本文ハッシュをキャッシュ。同一 URL を再取得した際に内容が変わっていなければスキップ。
- `--diff-only` 指定時は、変化があった場合のみ `*_diff.md` を別途生成（unified diff 形式）。
- 実行末尾に Gemini API のトークン使用量と概算コストを表示（`--no-cost` で抑止可）。
- `convmd find "<キーワード>"` で既存の出力フォルダ配下を全文検索（ripgrep があれば自動使用）。

### 📤 出力フォーマット (`--format`)
- `md`（既定）、`json`（フロントマター + 本文を構造化した配列）、`epub` / `pdf`（要 `pandoc`、PDF は xelatex が必要）。

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

### 古典籍の現代語訳併記モード (`--bilingual`)
国書データベース（IIIF）に対して `--bilingual` を渡すと、OCR で翻刻した古典日本語/漢文の直後に、Gemini が生成した現代語訳を blockquote で併記します。

```bash
uv run python -m convmd.cli https://kokusho.nijl.ac.jp/biblio/100243699/ --bilingual
```

### 差分追跡 (`--diff-only`) / 全文検索 (`convmd find`)

```bash
# 1 回目（通常通り output/ に保存）
uv run python -m convmd.cli https://example.com/news

# 2 回目以降、内容が変わったときだけ *_diff.md を出力
uv run python -m convmd.cli https://example.com/news --diff-only

# 既存の出力フォルダ全体を全文検索
uv run python -m convmd.cli find "国書" --ignore-case --limit 20
```

### 出力フォーマットの切替 (`--format`)
```bash
uv run python -m convmd.cli https://zenn.dev/.../slug --format json   # 構造化JSON
uv run python -m convmd.cli ./output/*.md --format epub               # pandoc 必須
```

### YAML 設定ファイル (`--config`)
CLI 引数が多くなる場合、YAML ファイルにデフォルトを書いておけます。優先度は **CLI 引数 > `--config <path>` > `./.convmd.yaml` > `~/.convmd.yaml`** です。

```yaml
# ~/.convmd.yaml もしくは ./.convmd.yaml
obsidian_vault: ~/Obsidian/MyVault
output_dir: ./output
auto_link: true
normalize_tags: true
tag_similarity_cutoff: 0.9
slack_webhook: https://hooks.slack.com/services/...
podcast_limit: 3
```

キー名は CLI のフラグ名(`--obsidian-vault` → `obsidian_vault`)と同じ snake_case を使います。未知のキーは警告ログを出して無視されます。

### Obsidian Vault のタグ正規化 (`--normalize-tags`)
`--auto-link` で AI 生成タグを使う際、`--normalize-tags` を有効にすると **既存 Vault のタグ集合と照合してタグを正規化** します。

- 大文字小文字違い: `python` → `Python`(既存 Vault の表記に統一)
- ハイフン/アンダースコア違い: `machine_learning` → `machine-learning`
- 日本語タグ: 完全一致のみ(fuzzy マッチによる誤マージを回避)

しきい値は `--tag-similarity-cutoff 0.85`(既定)で調整できます。`0.0–1.0`、高いほど厳密。

```bash
uv run python -m convmd.cli https://example.com/article \
    --auto-link --normalize-tags \
    --obsidian-vault ~/Obsidian/MyVault
```

### TLS 設定
既定では証明書検証が有効です。社内ネットワーク等で必要な場合に限り、環境変数 `CONVMD_INSECURE_SSL=1` で検証を無効化できます。

---

## 🏗 アーキテクチャと品質基準

このプロジェクトは `python-safe-coding` 規約に準拠し、以下の基準で実装されています。
- 厳格な型ヒント (Type Hints) の適用と `mypy` (strict) による検証
- `ruff` による高速な静的解析とフォーマット
- 環境非依存（Mac/Windows）のパス操作 (`pathlib.Path`)
- 安全で高速なHTTP通信 (`httpx`)、TLS 検証は既定で有効
- スケーラブルで再利用性の高いモジュール構成（旧 `legacy/` スクリプトの廃止）

### モジュール構成

```
src/convmd/
├── cli.py            # エントリポイント（薄い）
├── cli_args.py       # argparse + RunConfig dataclass
├── pipeline.py       # extract → diff → transform → link → summary → dispatch
├── routing.py        # URL ドメイン別の動的ディスパッチ（プラグイン追加に強い）
├── constants.py      # サフィックス・モデル名・タイムアウトの単一の真実
├── config.py         # 出力先解決（副作用なし）
├── exporters/        # md / json / pandoc(epub,pdf)
├── commands/         # find サブコマンド等
├── core/
│   ├── http.py       # 集中化された httpx ヘルパー（TLS 設定込み）
│   ├── gemini.py     # Gemini API 集中化 + UsageTracker（コスト集計）
│   ├── cache.py      # SQLite ベースのキャッシュ & unified diff
│   ├── crawler.py    # 同一ドメインBFSクローラ
│   ├── iiif.py       # IIIF マニフェスト処理 + 任意の bilingual OCR
│   ├── ocr.py        # OCR の薄いラッパ
│   ├── transform.py  # transform / auto-link / summary
│   ├── download.py   # 画像/HTML 取得の互換シム
│   └── utils.py      # フロントマター / ファイル名サニタイズ
├── parsers/          # 各プラットフォーム別のパーサ群
│   ├── general.py / office.py
│   ├── media/        # zenn, qiita, wikipedia, kokusho, audio, hatena, substack, medium, speakerdeck, podcast
│   └── sns/          # note, twitter, youtube, github, reddit, hackernews
└── integrations/     # notebooklm / obsidian / slack
```
