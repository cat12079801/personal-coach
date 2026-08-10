# 08. 未決定の設計判断

制約（[03-constraints.md](03-constraints.md)）では決まりきらず、実装中に判断が必要になったもの。

---

## OD-1: メニュー再生成のリクエストを誰が拾うか

**状態:** ⬜ 未決定（マイルストーン 6 で決める）

PWA は `regenerate_requests` に 1 行入れるところまで実装済み
（[0003_regenerate_requests.sql](../supabase/migrations/0003_regenerate_requests.sql)）。
**このリクエストを処理する側はまだ無い。**

独自バックエンドを持たない方針なので、PWA から直接 GitHub Actions を起動することはできない
（`workflow_dispatch` を叩くにはトークンが要るが、フロントに置けば公開されてしまう）。

### 案 A: ポーリングするワークフローを足す（推奨）

15 分おきに起動し、未処理のリクエストがあれば再生成する。

- 実装が単純で、新しい資格情報が要らない
- public リポジトリなので実行時間は無料
- 反映は最大 15 分待ち。無駄な起動が 1 日 96 回

### 案 B: Supabase Database Webhook から `repository_dispatch` を叩く

`regenerate_requests` への INSERT をトリガーに、pg_net で GitHub API を呼ぶ。

- 即時に反映される。無駄な起動もない
- GitHub の PAT を Supabase Vault に置く必要がある。資格情報が 1 つ増える
- pg_net と Vault の設定が増え、動作確認の経路が長くなる

### 案 C: Edge Function を挟む

方針（「独自バックエンドは作らない」）に反するので採らない。

> 案 A で始め、待ち時間が実際に不便なら案 B に移す。

---

## OD-2: PWA のログイン方式

**状態:** 🚧 暫定でメール + パスワード

[session.svelte.ts](../web/src/lib/session.svelte.ts) に暫定実装がある。
差し替える場合も `signIn()` だけを直せばよい。

- サインアップは無効化する運用なので、アカウントは Supabase ダッシュボードから手で作る
- メール配信に依存しないため設定が最も少ない
- マジックリンクにすればパスワード管理が要らなくなる。iOS の PWA からメールアプリへ
  往復する体験が許容できるかは実機で試して判断する

---

## OD-3: 手動ログの jsonb スキーマ

**状態:** 🚧 暫定

[logs/+page.svelte](../web/src/routes/logs/+page.svelte) の `FIELDS` が実体。
運用しながら項目を足し引きする前提で、DB 側は `jsonb` のままにしてある。
