# ご当地ゲームマップ（GitHub Pages版）

日本各地を舞台にしたゲームを探すクリッカブルマップです。

## できること

- デフォルメされた日本地図から47都道府県を選択
- 選択した県を「舞台になっている県」に含む作品を絞り込み
- 価格、配信形態、制作主体、舞台区分、キーワードを組み合わせて検索
- 県の選択状態をURLパラメーター（例：?pref=福岡県）に保持
- PC／スマートフォン、キーボード操作に対応
- 作品の配布元と作者ページへのリンク
- 管理人確認済（緑）／未確認（灰色）のバッジを各作品に表示
- サイト最上部に「試験運用中」の告知を表示
- ページ下部に運営者のXアカウントを表示

## GitHub Pagesへの設置

このフォルダの中身をすべてGitHubリポジトリの公開対象フォルダへ配置します。

    index.html
    games.json
    assets/
      japan-prefectures.svg

リポジトリの Settings → Pages → Build and deployment → Deploy from a branch で
配置先ブランチ（例：main）とフォルダ（例：/(root)）を選択してください。
ビルド処理や外部JavaScriptライブラリは不要です。

## ローカルで試す

ブラウザからHTMLを直接開くと、ブラウザのセキュリティ制約でJSON／SVGが読み込めない場合があります。

フォルダ内で以下を実行し、http://localhost:8000/ を開いてください。

    python -m http.server 8000

## Notionからの自動更新

`scripts/export_notion.py` がNotion APIから全件（100件単位でページネーション）を取得して
`games.json` に書き出します。公開対象の条件はすべて満たす必要があります。

- `掲載判定` が **掲載対象**
- `配信ステータス` が **配信中**
- `無効` が **未チェック**

未確認の作品でも掲載対象なら掲載します。その場合は灰色の「○ 未確認」、
`管理人確認済` がチェックされていれば緑の「✓ 管理人確認済」と表示されます。
`掲載判定` が **保留** の作品は非公開のままです。

### 初回セットアップ（GitHubで一度だけ）

1. NotionのAPIトークンに、作品台帳への **読み取り権限** があることを確認します。
   Notionで作品台帳の「接続」からインテグレーションを追加する必要がある場合があります。
2. このGitHubリポジトリで **Settings → Secrets and variables → Actions → New repository secret** を開き、
   `NOTION_TOKEN` という名前でトークンを登録します。公開リポジトリのVariablesには入れないでください。
3. **Settings → Pages → Build and deployment → Source** を **GitHub Actions** に変更します。
   これは重要です。GitHub Actionsの`GITHUB_TOKEN`による自動コミットは、
   ブランチからのPagesビルドを新たに起動しないため、Pagesへの再デプロイも同じワークフローで行います。
4. リポジトリの **Actions → Sync Notion games and deploy Pages → Run workflow** から初回実行します。
   GitHub Actionsのログで「Notion ○件 → 公開 ○件」とPagesのデプロイ成功を確認してください。

`.github/workflows/sync-notion.yml` は毎日 **日本時間03:17** に実行され、
JSONが変わったときだけ`games.json`を自動コミットし、Pagesをデプロイします。
HTMLなどの公開ファイルをpushした場合や、Actions画面の手動実行でも更新されます。

Notion APIでエラーになった場合や公開件数が0件になる場合は、既存JSONを壊さず処理を停止します。
ただし同期が成功すると、Notionでの公開判定の変更はサイトに反映されます。

ローカルで動かす場合（Python 3.12、追加ライブラリ不要）：

```bash
export NOTION_TOKEN="（Notionのトークン）"
export NOTION_DATA_SOURCE_ID="41add27a-37b4-812d-a3e3-000bdb2e4ba6"
python scripts/export_notion.py --output games.json
python -m unittest discover -s tests -v
```

※ 現在GitHubにある初期`games.json`は手動生成のスナップショットです。
**初回のActions実行後**にNotionの最新情報へ切り替わります。

ゲーム情報は次の項目を持つJSONの配列です。

- title：タイトル
- creator：作者・スタジオ
- creatorUrl：作者ページ
- url：配布ページ
- prefectures：舞台になっている県の配列（複数可）
- region：舞台地域
- platforms：配信形態の配列（複数可）
- price：価格（無料、有料、不明）
- creatorType：制作主体
- settingType：実在地域、実在地域モデルなど
- releaseDate：配信開始日（YYYY-MM-DD）
- confirmed：管理人確認済（true／false）
- disabled：無効状態（trueなら表示しない。現在の公開JSONでは全作品false）

**注意：** games.jsonは誰でも読める公開ファイルです。未公開作品、Notionの管理用メモ、
個人情報、APIトークンは含めないでください。Notionトークンを使って自動同期する場合は
GitHub Secretsなどでサーバー側に保管してください。

## 地図素材・ライセンス

- デフォルメ都道府県日本地図：lalamalink
- 出典：https://github.com/lalamalink/japan-map-svg
- ライセンス：CC0 1.0 Universal
- デフォルメ地図のため、位置関係・面積は地理的に厳密ではありません。
