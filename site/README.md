# サイトの保守手順

## 公開構成

公開先は https://lkjsxc.github.io/a/ です。`site/build.ts`が原稿からHTMLを生成し、`site/style.css`を配信します。ブラウザー用のJavaScriptバンドルは生成しません。`catalog.json`と`build.json`は検証用のメタデータで、閲覧時には取得しません。

サイト名は「学習サイト」です。説明は具体的で通常の文体にし、宣伝的な見出し・比喩的な機能名・子ども向けの呼びかけを追加しません。機能を増やすより、原稿と目次の整理を優先します。

## ローカル確認

```sh
npm ci
npm run verify
npx playwright install chromium webkit
PORT=4197 npm run test:browser
npm run preview
```

`verify`は型検査、単体テスト、全ページ生成、リンク・アンカー・ルビ・配布ファイルの検査を行います。ブラウザーテストはChromiumとWebKitで実施し、JavaScript無効、キーボード操作、幅320〜1440px、印刷用CSS、アクセシビリティを確認します。

`PORT`はプレビューのポートを変更します。テスト時は既存サーバーを使い回さず、対象の作業ツリーから起動します。

```sh
SITE_URL=https://example.com/ npm run build
node site/check.ts
npm run build
BASE_URL=https://lkjsxc.github.io/a/ npm run test:browser
```

最後のコマンドは公開済みサイトの検証です。公開反映を確認してから実行します。

## 原稿・配布データ

社会は`social-studies/source/`を編集し、同ディレクトリのREADMEに従って生成します。既存のPython生成器はAnkiパッケージとオフライン教材の生成に使用します。社会の単元ID・カードID・GUIDを変更しないでください。

ルビの正本は`editorial/ruby.json`です。社会のZIPには再生成用のコピー`ruby-policy.json`を含めます。ルビ辞書の変更後は次を実行してください。

```sh
node site/normalize-content.ts
python social-studies/tools/build.py --verify-anki --verify-render
node site/normalize-content.ts --checksums
npm run verify
npm run test:browser
```

上記のPythonコマンドは必要パッケージを入れた仮想環境内で実行します。AnkiバックエンドとPython版Playwrightが必要です。オプションを省いた生成では、未実施の検査を成功と記録しません。

理科の元データは`000005/data/science_cards_master.json`とCSVです。正規化処理はカード数・本文の基底文字列を検査し、関連するCSV・TSV・Markdownを更新します。旧`science_cards.xlsx`は2026年7月版の保存用ファイルとして保持し、公開配布から除外しています。現在の編集用配布形式は全項目CSVです。

## 公開時の不変条件

HTMLページは本文を直接含み、JavaScript・フォーム・独自設定UIを持ちません。ソースディレクトリ、実行コード、秘密情報、旧Excelファイルは配布対象にしません。既存の教材URL、全76社会単元、全171理科読み物ページ、全5,204枚のカードを保ちます。

確認問題の解答表示はネイティブHTML、印刷はCSSだけで実現します。CSSの対応差がありうるため、対応ブラウザーを変更したときは閉じた解答の印刷表示も再検査してください。

`_site/`・ブラウザーのトレース・スクリーンショット・個人の学習記録はコミットしません。検証結果を報告するときは、検証対象のコミットと実施範囲を明記してください。
