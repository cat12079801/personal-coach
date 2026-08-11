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

**状態:** ✅ 決定（Google OAuth のみ）

当初はメール + パスワードを暫定で入れていたが、成立しないことが判明した。
相乗り先の count-upper が Google SSO を使っており、対象アカウント（`auth.users` の行）は
Google の identity に紐づくだけで**パスワードを持たない**ため。

- Google provider はプロジェクト側で既に有効。追加設定は不要
- count-upper は Next.js のサーバルートで認可コードを交換しているが、こちらは静的 SPA な
  ので `detectSessionInUrl`（PKCE）でブラウザ側で交換する
- `Authentication > URL Configuration > Redirect URLs` に戻り先の許可が必要

### 残る懸念: iOS のホーム画面 PWA での OAuth

standalone 表示の PWA から OAuth に飛ぶと、戻りが PWA ではなく Safari になることがある。
実機で確認する（マイルストーン 5）。

問題が出た場合の緩和策:

- セッションは localStorage に永続化され自動リフレッシュされるので、**ログインは事実上初回のみ**。
  日常運用では OAuth の往復が発生しない
- それでも詰まるならマジックリンクを検討する

---

## OD-3: 手動ログの jsonb スキーマ

**状態:** 🚧 暫定

[logs/+page.svelte](../web/src/routes/logs/+page.svelte) の `FIELDS` が実体。
運用しながら項目を足し引きする前提で、DB 側は `jsonb` のままにしてある。
