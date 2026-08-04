# 美容室サイト量産 → 営業提案 → 月額運用 業務フロー

Google マップで見つけた「口コミはあるが公式サイトを持っていない美容室」向けに、
サンプルサイトを量産して営業し、契約後は月額運用に移行するための一式です。

現在 `data/salons.json` には鹿児島県内で見つけた **14店舗**（口コミが少なく、HP未確認・
未保有の可能性が高い候補）の実データが入っており、`data/generated_copy.json` には
その14店舗ぶんのサイト用コピー（サンプル）がすでに入っています。
`python3 scripts/build_sites.py` を実行するだけで、14サイトすべてがこの場で確認できます。

---

## 1. フォルダ構成

```
salon-site-generator/
├── data/
│   ├── salons.json          # 店舗の事実情報（店名・住所・電話・営業時間など）
│   └── generated_copy.json  # Claudeが生成したサイト用コピー（店舗IDごと）
├── templates/
│   └── salon_template.html  # 全店舗共通の1ページテンプレート（Jinja2）
├── scripts/
│   ├── generate_copy.py     # data/salons.json → Claude API → generated_copy.json
│   ├── build_sites.py       # data + copy → templates → output/<id>/index.html
│   └── requirements.txt
├── output/                  # ビルド結果（このフォルダをGitHub Pagesで公開する）
└── .github/workflows/deploy.yml   # push すると自動ビルド・自動公開
```

---

## 2. 業務フロー全体像

```
① 候補発掘        Google マップで「口コミあり・HPなし」の店舗をリストアップ
                   → data/salons.json に追記
                          │
② コピー生成       python3 scripts/generate_copy.py
                   （事実情報だけをClaudeに渡し、誇張・でっち上げ無しでコピー生成）
                          │
③ サイト量産       python3 scripts/build_sites.py
                   → output/<店舗id>/index.html が全店舗ぶん生成される
                   （すべて「提案用サンプル」の透かし付き）
                          │
④ 営業             生成したURL（or スクリーンショット）を店舗に見せて提案
                   「このサイトを月額4,000円で運用しませんか？」
                          │
⑤ 成約             --live フラグで透かしを外して本番ビルド → 独自ドメインで公開
                          │
⑥ 運用・課金       月額請求開始。軽微な更新は基本プラン内、
                   デザイン変更等はGitHub Issuesで受付→別途見積り
```

---

## 3. セットアップ

```bash
cd salon-site-generator
pip install -r scripts/requirements.txt
```

Claude API でコピーを生成する場合（新しい店舗を追加したときなど）:

```bash
export ANTHROPIC_API_KEY=sk-ant-xxxxxxxx
python3 scripts/generate_copy.py          # 未生成の店舗だけ生成
python3 scripts/generate_copy.py --force  # 既存も含めて全件再生成
```

サイトをビルドする（API不要、ローカルで完結）:

```bash
python3 scripts/build_sites.py
```

`output/` 以下に各店舗のサイトができるので、ブラウザで直接開くか、ローカルサーバーで確認できます:

```bash
python3 -m http.server 8000 --directory output
# → http://localhost:8000/ に一覧、http://localhost:8000/<id>/ に個別サイト
```

---

## 4. 新しい候補店舗を追加する

1. `data/salons.json` に1件追記する（`id` はURLに使うので半角英数字のスラッグにする）
2. `python3 scripts/generate_copy.py` でコピーを生成
3. `python3 scripts/build_sites.py` でサイトをビルド

`hours` は `[["月","9:00–19:00"], ["火","定休日"], ...]` の形式で7曜日ぶん入れてください。
`place_id` は Google マップの共有リンクや Places 検索結果から取得できます。

---

## 5. 営業（提案）フェーズの使い方

- ビルドしたサイトはすべて **「提案用サンプルページ」の透かしバナー付き** で出力されます
  （`templates/salon_template.html` の `is_demo` 分岐）。無断で本番公開しているように
  見せないための安全装置なので、営業段階では外さないでください。
- `output/<id>/` を GitHub Pages の一時プレビュー、または Netlify Drop 等にアップロードして
  URL を発行し、その URL を店舗に見せながら提案するのが一番効果的です。
- 提案メッセージの例（そのまま使えるたたき台）:

  > 突然のご連絡失礼いたします。貴店のGoogleマップの口コミを拝見し、
  > 素敵なサロンだと思いご連絡しました。まだ公式サイトをお持ちでないようでしたので、
  > 掲載されている情報をもとに試作のページを作成いたしました。
  > よろしければご覧ください：[URL]
  > もし気に入っていただけましたら、月額4,000円で運用（ドメイン維持・軽微な更新込み）
  > させていただくプランをご案内できます。ご不要でしたらそのまま削除いたしますので
  > お気軽にご判断ください。

---

## 6. 成約後：本番公開フェーズ

透かしを外して本番用にビルドする:

```bash
python3 scripts/build_sites.py --live hair-salon-lego
```

このコマンドを実行した店舗だけ `is_demo=false` になり、透かしバナーとサンプル注記が消えます。

**独自ドメインで公開する場合（GitHub Pages）:**
1. リポジトリの Settings → Pages で `output/` を公開対象に設定
2. 店舗ごとに専用ドメイン／サブドメインを使いたい場合は `output/<id>/CNAME` に
   ドメイン名を1行書く（例: `sample-salon.com`）
3. ドメイン側のDNSに `A` レコード（GitHub Pages IP）または `CNAME` を設定

`.github/workflows/deploy.yml` を有効にしておけば、`data/` や `templates/` を更新して
push するだけで自動的に再ビルド・再公開されます（Secrets に `ANTHROPIC_API_KEY` を登録）。

---

## 7. 運用開始後のカスタマイズ対応フロー

1. 店舗から「営業時間を直してほしい」「写真を追加したい」等の要望を受ける
2. 内容を GitHub の Issue として起票（1店舗1リポジトリ運用なら Issue、
   monorepo 運用ならラベルで店舗を識別）
3. 軽微な変更（`data/salons.json` の値の書き換えだけで済むもの）は基本プラン内で対応
4. デザイン変更・新規ページ・独自機能などは別途見積り → 合意後に対応
5. 対応後、`build_sites.py --live <id>` で再ビルド → push で自動反映

---

## 8. 料金モデルの目安

| 項目 | 内容 | 原価感 |
|---|---|---|
| ホスティング | GitHub Pages | 無料 |
| 独自ドメイン | 年1,000〜1,500円程度 | 月換算 100〜150円 |
| SSL証明書 | GitHub Pages標準機能 | 無料 |
| 軽微な更新対応 | 営業時間・電話番号の修正など | 人件費のみ |

月額4,000円のうち、上記の実費を差し引いた分が運用・サポートの利益になります。
**基本プランに含む範囲**と**別料金になる範囲**は、前回の提案時点で店舗側に明示しておくと
トラブルになりにくいです（README冒頭の表を参考に、契約書や見積書に転記してください）。

---

## 9. 実行前に必ず確認したいこと（法的・倫理的チェックリスト）

- [ ] **公開前に必ず店舗の同意を得る。** サンプル段階では `is_demo=true` のままにし、
      検索エンジンにインデックスされないよう配慮する（例: 該当ページに
      `<meta name="robots" content="noindex">` を追加する、専用のプレビューURLのみ共有する等）。
- [ ] **Google口コミの本文をそのまま転載しない。** 本テンプレート・生成スクリプトは
      口コミ本文をそもそも生成AIに渡さない設計にしていますが、手動で追記する場合も注意してください。
- [ ] **掲載情報（営業時間・電話番号など）は公開前に店舗へ最終確認を取る。** 誤った情報の
      公開は信用問題につながります。
- [ ] **月額契約には簡単な利用規約・解約条件を用意する。** 特定商取引法表記が必要な
      ケースもあるため、不安があれば専門家に確認してください。

---

## 10. トラブルシューティング

- `generate_copy.py` が `ANTHROPIC_API_KEY` エラーで止まる → 環境変数が未設定です。
  ローカルでは `export ANTHROPIC_API_KEY=...`、GitHub Actionsでは Secrets に登録してください。
- `build_sites.py` が `[skip]` を出す → その店舗IDぶんの `generated_copy.json` がまだ
  ありません。先に `generate_copy.py` を実行してください。
- 日本語フォントが崩れる → テンプレートは Google Fonts（Shippori Mincho / Zen Kaku Gothic New）
  をCDN経由で読み込むため、オフライン環境ではプレビューが崩れます。本番公開先（GitHub Pages等）
  では問題ありません。
