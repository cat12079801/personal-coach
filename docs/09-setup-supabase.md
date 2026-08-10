# 09. Supabase セットアップ手順

マイルストーン 1 の前提作業。**上から順に実施する。**

ダッシュボードのラベルは変わることがある。見つからなければ近い名前の項目を探すこと。

---

## 1. プロジェクトを作成する

<https://supabase.com/dashboard> → New project

| 項目 | 値 |
|---|---|
| Name | `personal-coach` |
| Region | Northeast Asia (Tokyo) |
| Database Password | 自動生成してパスワードマネージャに保存する |

**DB パスワードは後から表示できない。** ここで必ず保存する。CLI からマイグレーションを
適用するときに使う。

作成後、`Settings > General` の Project ID（`abcdefghijklm` のような文字列）を控える。
以降 `<project-ref>` と表記する。

## 2. マイグレーションを適用する

`supabase/migrations/` の 3 本を **0001 → 0002 → 0003 の順に**適用する。

### 方法 A: CLI（推奨）

リポジトリのマイグレーションをそのまま流せる。以降の追加も `db push` だけで済む。

```bash
brew install supabase/tap/supabase
```

```bash
supabase login
```

```bash
supabase init
```

```bash
supabase link --project-ref <project-ref>
```

`link` で 1 の DB パスワードを聞かれる。

```bash
supabase db push
```

`supabase init` が `supabase/config.toml` を作る。これはコミットしてよい。

### 方法 B: SQL Editor

CLI を入れたくない場合。ダッシュボードの `SQL Editor` に、以下を**この順で**貼って実行する。

1. `supabase/migrations/0001_init.sql`
2. `supabase/migrations/0002_owner_only_rls.sql`
3. `supabase/migrations/0003_regenerate_requests.sql`

### 確認

`SQL Editor` で以下を実行する。

```sql
select tablename, policyname, coalesce(qual, with_check) as cond
from pg_policies where schemaname = 'public'
order by tablename, policyname;
```

- ポリシーが **11 本**あり、`cond` がすべて `is_owner()` になっている
- `garmin_tokens` と `app_owner` は 1 本も出てこない（クライアントから触れない）

## 3. サインアップを無効化する

**これが主たる防御である。** これをやらないと、誰でもアカウントを作って全データにアクセスできる。

`Authentication` → `Sign In / Providers`（または `Settings`）→ Email プロバイダの
**Allow new users to sign up** を **オフ**にする。

## 4. 自分のアカウントを作る

`Authentication` → `Users` → `Add user` → `Create new user`

- メールアドレスとパスワードを入力する
- **Auto Confirm User** を有効にする（確認メールを踏まずに使えるようにする）

## 5. 所有者として登録する

`SQL Editor` で実行する。メールアドレスは 4 で作ったもの。

```sql
insert into app_owner (user_id)
select id from auth.users where email = 'あなたのメールアドレス';
```

確認する。

```sql
select o.user_id, u.email from app_owner o join auth.users u on u.id = o.user_id;
```

**1 行返ってこなければ失敗している。** `app_owner` が空の間は `is_owner()` が常に false を返し、
誰も読み書きできない（fail-closed）。

## 6. API キーを取得する

`Settings` → `API Keys`

| キー | 形式 | 用途 | 置き場 |
|---|---|---|---|
| publishable | `sb_publishable_...` | フロント | Cloudflare Pages のビルド環境変数 / `web/.env.local` |
| secret | `sb_secret_...` | バッチ | GitHub Secrets / `.env` |

`Legacy API Keys` タブの `anon` / `service_role` は**使わない**。2026 年末で廃止される。

**secret キーは RLS をバイパスする。** フロントや public なファイルに絶対に置かない。

## 7. 疎通を確認する

```bash
cd web
cp .env.example .env.local
```

`.env.local` に `VITE_SUPABASE_URL` と `VITE_SUPABASE_PUBLISHABLE_KEY` を書く。

```bash
npm run dev
```

<http://localhost:5173> を開き、4 で作ったアカウントでログインする。

- ログインできる → 3〜5 が正しい
- ログインできるが各画面が空でエラーも出ない → 正常（データがまだ無い）
- ログインできるがエラーが出る → 5 の `app_owner` 登録を確認する

### RLS が効いていることの確認

`SQL Editor` ではなく、ブラウザの devtools コンソールでログアウト状態で叩くのが確実。
未ログインで `activities` を読もうとして 0 件かエラーになれば期待どおり。

---

## 次

[05-roadmap.md](05-roadmap.md) のマイルストーン 1。

リポジトリ直下の `.env` を作る（`config.py` が読む。gitignore 済み）。

```bash
cp .env.example .env
```

`SUPABASE_URL` と `SUPABASE_SECRET_KEY` を書いたら、Garmin トークンを投入する。

```bash
cd batch && uv run python scripts/bootstrap_garmin_token.py
```
