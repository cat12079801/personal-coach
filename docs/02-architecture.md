# 02. アーキテクチャ

## 技術スタック（確定）

| レイヤ | 採用 | 補足 |
|---|---|---|
| ホスティング | Cloudflare Pages | 静的配信のみ。**API サーバは持たない** |
| DB / 認証 | Supabase | Postgres + Auth + RLS |
| バッチ実行基盤 | GitHub Actions の cron | **public リポジトリ**（実行時間無料無制限） |
| バッチ言語 | Python | |
| フロント | PWA | フレームワークは任意（SvelteKit / React + Vite 等） |
| 通知 | Web Push | VAPID、`pywebpush` |
| Garmin アクセス | `garminconnect` | cyberjunky/python-garminconnect |

フロントは `supabase-js` で Supabase を直接読む。**独自バックエンドは作らない。**

## 全体構成

```
                      ┌──────────────────────────────┐
                      │  GitHub Actions (public)     │
   03:00 JST ────────▶│  daily-ingest                │
   (cron 0 18 * * *)  │   1. Garmin 差分同期          │──▶ Garmin Connect
                      │   2. ラン splits 追い取得      │    (garminconnect / curl_cffi)
                      │   3. Google Calendar (.ics)   │──▶ 非公開 iCal URL
                      │   4. メニュー生成（ルール）    │
                      │   5. keepalive コミット        │
                      └──────────┬───────────────────┘
                                 │ secret key
                                 ▼
                      ┌──────────────────────────────┐
                      │  Supabase (Postgres + Auth)  │
                      │  activities / running_details│
                      │  *_logs / daily_menus        │
                      │  push_subscriptions          │
                      │  garmin_tokens               │
                      └──────────┬───────────────────┘
                                 │ publishable key + RLS
   08:00 JST ────────▶ daily-notify ──▶ Web Push ──▶ iOS ホーム画面 PWA
   (cron 0 23 * * *)     （要約のみ）                    │
                                                        ▼
                                        Cloudflare Pages（静的 PWA）
                                        起動時に Supabase から当日メニューを取得
```

## なぜこの構成なのか

要点だけ。詳細と却下理由は [03-constraints.md](03-constraints.md) と [adr/](adr/) にある。

- **Garmin アクセスが GitHub Actions に固定される。** `garminconnect` はネイティブ C 拡張
  （`curl_cffi`）に依存するため、Cloudflare Workers / Supabase Edge Functions では動かない。
  ここが構成全体を決めている
- **API サーバを持たないのは、持つ必要がないから。** 書き込みはバッチ（service_role）、
  読み取りはフロント（anon + RLS）で完結する
- **push はトリガーと要約のみを運ぶ。** データ本体は 03:00 の時点で DB にある

## 疎結合の方針

2026 年 3 月に Garmin 側の認証変更でエコシステムが一斉に壊れた前例がある。
ライブラリの破壊的変更は起こる前提で設計する。

- Garmin に触れるコードは `batch/src/personal_coach/garmin/` に閉じ込める
- 取得した JSON は `activities.raw` にそのまま保存し、正規化に失敗しても後から再パースできるようにする
- メニュー生成は Garmin のレスポンス形状ではなく、正規化済みの内部表現を入力にする
