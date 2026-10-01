# 検証記録

確認基準日：2026-09-30

この記録は生成プログラムが実際に成功した検査と、その限界を示します。外部の専門家の査読や、模試集団での難易度調査を意味しません。

## 収録数

- lessons: 76

- lesson_counts: {'foundation': 4, 'geography': 27, 'history': 27, 'civics': 18}

- lesson_cards: 1246

- atlas_cards: 47

- anki_cards: 1293

- lesson_questions: 228

- worked_examples: 12

- mock_exams: 3

- mock_questions: 72

- timeline_entries: 119

- reading_characters: 64643

## 自動検査

- 76 expected lessons and order

- unique lesson/card identifiers and normalized keywords

- prerequisite references and acyclic graph

- source reference IDs resolved

- 3 answered questions per lesson

- 3 assessments x 24 questions; each exactly 100 points

- CSV/TSV exact round-trip including HTML and tags

- APKG ZIP CRC and SQLite integrity; note/card/GUID counts

- keyword-only question template

- ruby boundary and nesting regression checks

- worked arithmetic and mock-exam numerical spot checks

## Ankiの検証範囲

APKG内のSQLiteデータベースを開き、ノート数・カード数・一意なGUIDがそれぞれ1,293件で一致し、整合性検査が成功しました。CSV・TSVを再度読み込み、全フィールドの一致を確認しました。

これはデスクトップ・スマートフォンのAnki画面での操作や同期の試験ではありません。更新前にはバックアップを取り、初回は数枚を開いてルビと裏面を確認してください。

## 内容面の点検

本文では、鎖国と断交、署名と発効、公布と施行、総議員と出席議員、割合と実数、政府の立場と現実の管理などを区別して記述しています。歴史の説明を一つの原因や一人の功績だけへ単純化しないよう注意しています。

計算例・グラフの架空データを明示し、総合問題の配点合計と基本計算を確認しました。個々の文の正確さを自動検査だけで保証することはできません。誤りや読みにくさが見つかった場合は、原稿を直して再生成してください。

## 地図

{"world_countries": 177, "japan_prefectures": 47, "source": "Natural Earth 110m admin0 / 10m admin1, public domain"}

原図を47都道府県のコードで抽出したことを検査しています。地図は位置学習用で、一部の離島を省略します。国境・領有権の厳密な判断の資料には用いません。

## 配布形式

Markdown・オフラインHTML・APKG・CSV・TSV・ZIPを生成します。PDFは含みません。印刷にはブラウザーの印刷機能を利用できます。フォントファイルと個人データは含みません。

## Anki実装による取り込み試験

Anki Python 26.9.3 の実際の取り込み処理を、個人データを含まない一時コレクションで実行しました。初回取り込み、同一APKGの再取り込み、内容変更を含む更新、試験用の復習状態の保持を検査しました。詳しい対象ファイルと結果は ANKI_IMPORT_TEST.json に記録しています。デスクトップ画面・実機スマートフォン・同期の試験ではありません。

## ブラウザー表示試験

Chromiumでデスクトップ幅・スマートフォン幅を確認し、単元数、表、スクリプトがないこと、解答の開閉、画像読込、横方向のはみ出し、印刷時の解答表示を検査しました。実機のSafariやAnkiアプリの画面を試験したものではありません。詳細は BROWSER_TEST.json にあります。


生成済みのローカルファイル・画像リンクについて、参照先の存在を検査して成功しました。
