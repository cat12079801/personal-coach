# personal-coach

Garmin Connect のアクティビティ記録と手動登録のワークアウト記録を集約して Web 上で閲覧し、
毎朝その日のトレーニングメニューを自動生成して通知する個人用アプリ。利用者は本人 1 人のみ。

## ドキュメント

| ファイル | 内容 |
|---|---|
| [docs/01-overview.md](docs/01-overview.md) | 目的・対象種目・自動化要件 |
| [docs/02-architecture.md](docs/02-architecture.md) | 技術スタックと全体構成 |
| [docs/03-constraints.md](docs/03-constraints.md) | **踏んではいけない制約（最重要）** |
| [docs/04-data-model.md](docs/04-data-model.md) | データモデルと設計上の必須ポイント |
| [docs/05-roadmap.md](docs/05-roadmap.md) | 実装順序とマイルストーン |
| [docs/06-poc-notes.md](docs/06-poc-notes.md) | PoC 結果の記録先（未確定事項の潰し込み） |
| [docs/07-garmin-api.md](docs/07-garmin-api.md) | 検証済み `garminconnect` API 一覧 |
| [docs/08-open-decisions.md](docs/08-open-decisions.md) | 未決定の設計判断 |
| [docs/09-setup-supabase.md](docs/09-setup-supabase.md) | Supabase セットアップ手順 |
| [docs/adr/](docs/adr/) | 却下済み選択肢を含む意思決定記録 |

**DB は既存の Supabase プロジェクトに `coach` スキーマで相乗りしている。**
理由と注意点は [ADR-0006](docs/adr/0006-share-existing-supabase-project.md)。

実装に着手する前に必ず [docs/03-constraints.md](docs/03-constraints.md) を読むこと。
そこに書かれた選択肢はすべて調査済みで却下されている。

## リポジトリ構成

```
batch/       GitHub Actions から実行する Python バッチ（Garmin 取り込み / メニュー生成 / 通知）
web/         PWA（SvelteKit + adapter-static。Cloudflare Pages に静的配信）
supabase/    DB マイグレーション
.github/     ワークフロー定義（cron・keepalive・失敗通知）
docs/        設計ドキュメント
```

## セットアップ

### 1. Supabase

プロジェクト作成 → マイグレーション適用 → サインアップ無効化 → 所有者登録 → API キー取得。

**手順は [docs/09-setup-supabase.md](docs/09-setup-supabase.md) に全部書いてある。**

アクセス制御（サインアップ無効化と `app_owner` 登録）は省略できない。
省くと誰でもアカウントを作って全データにアクセスできる。

### 2. Garmin トークンの初期投入

初回ログインは MFA の対話が必要なためローカルで実施する。

```bash
cd batch
uv sync
uv run python scripts/bootstrap_garmin_token.py
```

対話でメールアドレス・パスワード・MFA コードを入力すると、生成されたトークンが
Supabase の `garmin_tokens` テーブルに投入される。以降はバッチが自動でリフレッシュし書き戻す。

### 3. GitHub Secrets

| Secret | 用途 |
|---|---|
| `SUPABASE_URL` | Supabase プロジェクト URL |
| `SUPABASE_SECRET_KEY` | バッチからの書き込み用（`sb_secret_...`） |
| `GARMIN_EMAIL` / `GARMIN_PASSWORD` | トークン失効時の再ログイン用 |
| `GOOGLE_CALENDAR_ICS_URL` | カレンダーの非公開 iCal URL（実質的な認証情報） |
| `VAPID_PUBLIC_KEY` / `VAPID_PRIVATE_KEY` / `VAPID_SUBJECT` | Web Push |
| `DISCORD_WEBHOOK_URL` | バッチ失敗通知 |

**このリポジトリは public である**。ログに Secrets を出力しないこと。詳細は
[docs/03-constraints.md](docs/03-constraints.md) の「5. GitHub Actions の 60 日自動無効化」を参照。

## PWA

```bash
cd web
npm install
cp .env.example .env.local   # 値を埋める
npm run dev
```

Cloudflare Pages の設定と iOS 対応の要点は [web/README.md](web/README.md) を参照。

## バッチ

| ワークフロー | cron (UTC) | JST | 内容 |
|---|---|---|---|
| [daily-ingest.yml](.github/workflows/daily-ingest.yml) | `0 18 * * *` | 03:00 | Garmin 取り込み + メニュー生成 + keepalive |
| [daily-notify.yml](.github/workflows/daily-notify.yml) | `0 23 * * *` | 08:00 | Web Push 送信 |

GitHub Actions の cron は最大数十分ずれる。3 時 → 8 時で 5 時間のバッファがあるので実害はない。

## 現在地

[docs/05-roadmap.md](docs/05-roadmap.md) の進捗表を参照。
