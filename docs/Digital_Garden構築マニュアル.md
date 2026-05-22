# Obsidian Digital Garden 完全構築マニュアル

このマニュアルは、Obsidianのノートを無料でWeb上に公開できるプラグイン「Digital Garden」のセットアップ手順を解説したものです。

## 概要
* **必要なもの**: Obsidianアカウント、GitHubアカウント、Vercelアカウント
* **費用**: 完全無料
* **所要時間**: 約15分〜30分

---

## ステップ1：Obsidianにプラグインを導入する

1. Obsidianを開き、左下の「歯車アイコン（設定）」をクリックします。
2. 左メニューから **「コミュニティプラグイン」** を選択します。
   * ※「セーフモード」がオンになっている場合は、オフ（無効化）にしてコミュニティプラグインを有効にしてください。
3. 「閲覧」ボタンをクリックし、検索窓に **`Digital Garden`** と入力します。
4. 検索結果から「Digital Garden」を選択し、**「インストール」**ボタンを押します。
5. インストールが完了したら、同じ場所にある**「有効化」**ボタンを押します。

---

## ステップ2：公開用のWebサーバー（Vercel）と保存庫（GitHub）を用意する

プラグインがObsidianから送信したデータを表示するための「Webサイトの土台」を作ります。

1. ブラウザで以下のDigital Garden公式テンプレートページにアクセスします。
   👉 [Digital Garden Template ページ](https://github.com/oleeskild/digitalgarden)
2. ページを少し下にスクロールし、**「Deploy」** という黒い三角形のVercelボタンをクリックします。
3. Vercelの画面が開きます。**「Continue with GitHub」** を選択し、GitHubアカウントでログインします（アカウントがない場合は作成してください）。
4. 「Create Git Repository」という画面が出たら、**Repository Name** に好きなサイト名（例：`awashi-wiki`, `my-digital-garden`）を入力し、**「Create」** をクリックします。
   * *※ これにより、あなたのGitHubに専用のデータ保存庫（リポジトリ）が作られます。*
5. デプロイ（構築）が始まり、数分待つと紙吹雪が舞って成功画面が表示されます。
   * *※ これでWebサイトの土台となるURL（例：`https://awashi-wiki.vercel.app`）が発行されました。*

---

## ステップ3：GitHubの「アクセス鍵（トークン）」を取得する

Obsidianアプリが、あなたのGitHub（Webサイトの裏側）に直接Markdownファイルを書き込めるようにするための「合鍵」を発行します。

1. ブラウザで GitHub の設定ページ [Personal Access Tokens (Tokens (classic))](https://github.com/settings/tokens) にアクセスします。
2. 画面右上の **「Generate new token」** をクリックし、**「Generate new token (classic)」** を選択します。
3. 設定項目を以下のように入力します。
   * **Note**: `Obsidian DG` （何の鍵かわかれば何でもOKです）
   * **Expiration** (有効期限): **`No expiration`** （無期限）を選択します。
4. 下に並んでいるチェックボックス（Scopes）の中から、**`repo`** という項目のチェックボックスのみにチェックを入れます（リポジトリの全権限を与えます）。
5. ページの一番下にある緑色の **「Generate token」** ボタンをクリックします。
6. `ghp_` から始まる長い英数字の文字列が表示されます。これが「トークン（合鍵）」です。
   * ⚠️ **【超重要】この文字列は今この画面でしか表示されません。必ずコピーして、安全な場所（メモ帳など）に一時保存してください。**

---

## ステップ4：Obsidianに設定を入力して、いざ公開！

1. Obsidianに戻り、設定画面の左メニューの少し下に追加された **「Digital Garden」** をクリックします。
2. 以下の3つの項目を正確に入力します。
   * **GitHub Username**: あなたのGitHubのユーザー名
   * **GitHub repo name**: ステップ2の「4」で入力したリポジトリ名（例：`awashi-wiki`）
   * **GitHub token**: ステップ3でコピーした `ghp_` から始まるトークン文字列
   * *※ 他の設定項目（サイト名やURLなど）は後からでも変更可能です。*
3. 設定画面を閉じます。

### ノートを公開する手順

1. Webに公開したいMarkdownファイルを開きます。
2. ファイルの先頭にあるプロパティ（YAML Frontmatter）に、以下の1行を追加します。
   ```yaml
   dg-publish: true
   ```
   * *※ これを書いたファイルだけがWebに公開されます。個人的なメモが勝手に公開されることはありません。*
3. Obsidianの左側にあるリボン（縦に並んだアイコン群）から、新しく追加された **「葉っぱのアイコン（Digital Garden）」** をクリックします。
4. 画面右側に「Publication Center」というパネルが開きます。
5. パネルの中にある **「Publish Notes」** ボタンをクリックします。
6. 「Published 1 notes」というような通知が出れば成功です！

数分後（Vercelの裏側の処理が終わった後）、あなたのVercelのURLにアクセスすると、そのノートが綺麗なWebサイトとして公開されていることが確認できます。

---

## （おまけ）さらに高度な使い方
* **一括公開**: 複数ファイルのプロパティに `dg-publish: true` をつけて「Publish Notes」を押せば、一気に何十記事も公開できます。
* **テーマの変更**: Obsidianの設定 > Digital Garden の「Appearance」タブから、サイトの見た目（テーマ）を変更できます。
