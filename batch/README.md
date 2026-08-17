# batch

GitHub Actions から実行する Python バッチ。

**Garmin にアクセスする処理は必ずここで動かす。** Cloudflare Workers / Supabase Edge Functions
では `curl_cffi` が動かない（[docs/03-constraints.md](../docs/03-constraints.md) の 1）。

## セットアップ

```bash
cd batch
uv sync
```

## 実行

```bash
uv run pc-ingest      # 取り込み + メニュー生成（03:00 JST 相当）
uv run pc-notify      # 通知送信（08:00 JST 相当）
uv run pc-regenerate  # 再生成リクエストの処理（15 分おき相当）
```

## スクリプト

| スクリプト | 用途 |
|---|---|
| `scripts/bootstrap_garmin_token.py` | Garmin トークンの初期投入（ローカル・MFA 対話あり） |
| `scripts/poc_dump_training_plans.py` | PoC-1: コーチのプランの取得元と形状を調べる |
| `scripts/poc_dump_activity_types.py` | PoC-2: 種目の `type_key` を調べる |

PoC の出力は `.poc-out/`（gitignore 済み）。**個人データなのでコミットしない。**

## パッケージ構成

```
personal_coach/
├── config.py         環境変数。ここで読んだ値はログに出さない
├── db.py             Supabase（secret key = service_role ロール、coach スキーマ）
├── cli.py            エントリポイント
├── ingest.py         取り込み（マイルストーン 3・未着手）
├── regenerate.py     再生成リクエストの処理（Garmin を引き直す）
├── calendar_ics.py   Google カレンダー（非公開 iCal URL）
├── garmin/           Garmin 依存はこの中に閉じ込める
│   ├── auth.py       ログイン + トークンの Supabase 往復
│   └── sync.py       差分同期・429 バックオフ
├── menu/rules.py     メニュー生成（マイルストーン 6・未着手）
└── push/sender.py    Web Push
```

## まだ実装していないもの

`ingest._normalize()` と `menu.rules.generate()` は `NotImplementedError` のまま。

**推測で実装しない。** API のレスポンス形状は PoC で実データをダンプして確認してから書く。
[docs/06-poc-notes.md](../docs/06-poc-notes.md) を参照。
