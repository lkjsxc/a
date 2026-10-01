# 学習サイト

社会・理科の本文、確認問題、Anki用データを掲載しています。

**[学習サイトを開く](https://lkjsxc.github.io/a/)**

[社会の目次](https://lkjsxc.github.io/a/social-studies/) / [理科の目次](https://lkjsxc.github.io/a/000005/) / [教材一覧](https://lkjsxc.github.io/a/library.html) / [ダウンロード](https://lkjsxc.github.io/a/downloads.html)

## 構成

HTMLとCSSによる静的なドキュメントサイトです。目次、本文、資料、確認問題、配布データを掲載しています。確認問題の解答と単元一覧の開閉にはHTML標準の`details`を使用しています。

サイト独自のJavaScript、検索アプリ、読了記録、ブックマーク管理、カード練習、テーマ設定、アカウント、アクセス解析ツールはありません。ページ内検索・ブックマーク・文字の拡大・印刷にはブラウザーの標準機能を利用してください。

## 教材

|場所|内容|
|---|---|
|[social-studies](social-studies/README.md)|中学校3年間の社会。76単元、確認問題228問、総合問題3回・72問、Ankiカード1,293枚|
|[000005](000005/README.md)|小学校・中学校の理科。本文・資料、全857枚のカードと基礎150枚の選択版|
|[000001.csv](000001.csv)|英単語・対訳2,286枚|
|[000002.csv](000002.csv)|初級英会話・語彙206枚|
|[000003.csv](000003.csv)|色彩理論・絵画62枚|
|[000004.json](000004.json)|基礎・地理・歴史500枚。JSONはAnkiに直接取り込む形式ではありません|

基礎150枚は理科857枚の一部です。重複して取り込まないでください。各データの取り込み方法と更新時の注意は科目別の案内を確認してください。

旧版のブラウザー内の学習記録は読み取りません。自動削除もしません。旧`review.html`は配布データへの静的な案内として残しています。

## 編集・検証

Webサイトの生成はNode.js 24とTypeScriptを使用します。これらは開発時だけの依存関係で、閲覧時にはHTML・CSS・画像しか読み込みません。

```sh
npm ci
npm run verify
npx playwright install chromium webkit
npm run test:browser
npm run preview
```

公開物は`_site/`に生成されます。`main`へのpush後、GitHub Actionsで検証した成果物だけをGitHub Pagesへ公開します。

[サイトの保守手順](site/README.md) / [文体・ルビの編集方針](editorial/README.md)

## 利用上の注意

個人制作の補助教材です。学校・入試主催者の公式教材ではなく、成績や合格を保証しません。出典、統計の基準日、制度の更新に注意してください。

[社会の出典](social-studies/SOURCES.md) / [理科の出典](000005/sources/SOURCES.md)

オリジナルの教材とコードは[Apache License 2.0](LICENSE)で公開しています。第三者資料にはそれぞれの利用条件が適用されます。
