# ご当地ゲームマップ（GitHub Pages版）

日本各地を舞台にしたゲームを探すクリッカブルマップです。

## できること

- デフォルメされた日本地図から47都道府県を選択
- 選択した県を「舞台になっている県」に含む作品を絞り込み
- 価格、配信形態、制作主体、舞台区分、キーワードを組み合わせて検索
- 県の選択状態をURLパラメーター（例：?pref=福岡県）に保持
- PC／スマートフォン、キーボード操作に対応
- 作品の配布元と作者ページへのリンク

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

## データの更新

games.json は **2026-11-16 時点のNotion作品台帳**から抽出したスナップショットです。
「掲載判定：掲載対象」かつ「配信ステータス：配信中」の31作品を収録しています。
公開前に作品情報、配信形態、リンク先をご確認ください。

Notionで作品を編集しても自動更新されません。新しい作品を反映するには
games.jsonを更新し、GitHubにコミットしてください。
将来的にはNotion APIとGitHub Actionsによる自動更新が可能です。

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

**注意：** games.jsonは誰でも読める公開ファイルです。未公開作品、Notionの管理用メモ、
個人情報、APIトークンは含めないでください。Notionトークンを使って自動同期する場合は
GitHub Secretsなどでサーバー側に保管してください。

## 地図素材・ライセンス

- デフォルメ都道府県日本地図：lalamalink
- 出典：https://github.com/lalamalink/japan-map-svg
- ライセンス：CC0 1.0 Universal
- デフォルメ地図のため、位置関係・面積は地理的に厳密ではありません。
