# ADR-0001: Garmin 取り込みは GitHub Actions 上の Python で実行する

- 状態: 採用
- 日付: 2026-08-10

## 背景

ホスティングは Cloudflare Pages、DB は Supabase。素直に考えれば取り込み処理も
Cloudflare Workers か Supabase Edge Functions に置きたい。

## 決定

**Garmin にアクセスする処理は必ず GitHub Actions 上の Python で実行する。**
リポジトリは public にする。

## 理由

`garminconnect` は `curl_cffi`（TLS フィンガープリント偽装のためのネイティブ C 拡張）に依存する。

| 実行環境 | ランタイム | 可否 |
|---|---|---|
| Cloudflare Workers | JS / WASM | ✗ |
| Cloudflare Python Workers | Pyodide | ✗ |
| Supabase Edge Functions | Deno | ✗ |
| GitHub Actions | ネイティブ Python | ✓ |

## 却下した選択肢

### 素の fetch で Garmin API を叩き直す

TLS フィンガープリントによる bot 検知で弾かれる。`curl_cffi` が存在する理由がこれ。

### 常時稼働のサーバ / VPS を立てる

個人用の日次バッチのために運用対象を増やす価値がない。

## 帰結

- public リポジトリなので Actions の実行時間は無料無制限
- 一方で **60 日間リポジトリ活動がないとスケジュールが自動無効化される**
  → keepalive が必要になる（[ADR は 03-constraints.md の 5 を参照](../03-constraints.md)）
- public なので Secrets の取り扱いに制約がかかる（`pull_request_target` 禁止、ログ出力禁止など）
- cron の発火が最大数十分ずれる。03:00 生成 → 08:00 通知の 5 時間バッファで吸収する
