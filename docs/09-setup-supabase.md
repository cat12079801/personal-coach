# 09. Supabase セットアップ手順

マイルストーン 1 の前提作業。**上から順に実施する。**

無料プランのプロジェクト数上限のため、**新規プロジェクトは作らず、
[count-upper](https://github.com/cat12079801/count-upper) が使っている既存プロジェクトに
`coach` スキーマで相乗りする**（[ADR-0006](adr/0006-share-existing-supabase-project.md)）。

ダッシュボードのラベルは変わることがある。見つからなければ近い名前の項目を探すこと。

---

## 1. 対象プロジェクトを確認する

<https://supabase.com/dashboard> で count-upper が使っているプロジェクトを開く。

`Settings > General` の Project ID（`abcdefghijklm` のような文字列）を控える。
以降 `<project-ref>` と表記する。

count-upper の `public.counters` / `public.count_logs` はそのまま残す。触らない。

## 2. マイグレーションを適用する

`supabase/migrations/` の 3 本を **0001 → 0002 → 0003 の順に**適用する。
すべて `coach` スキーマに作られるので、count-upper 側とは混ざらない。

### 方法 A: CLI（推奨）

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

`link` で DB パスワードを聞かれる。count-upper のセットアップ時に保存したもの。

```bash
supabase db push
```

> **注意:** 相乗り先には count-upper のマイグレーション履歴がある。
> `db push` は未適用のものだけを流すが、実行前に必ず差分の確認プロンプトを読むこと。
> count-upper 側のマイグレーションがこのリポジトリに無いため、
> 想定外の操作が出たら中断して方法 B に切り替える。

### 方法 B: SQL Editor（相乗りではこちらが安全）

ダッシュボードの `SQL Editor` に、以下を**この順で**貼って実行する。

1. `supabase/migrations/0001_init.sql`
2. `supabase/migrations/0002_owner_only_rls.sql`
3. `supabase/migrations/0003_regenerate_requests.sql`

履歴テーブルを触らないので、count-upper 側に影響しない。

### 確認

```sql
select tablename, policyname, coalesce(qual, with_check) as cond
from pg_policies where schemaname = 'coach'
order by tablename, policyname;
```

- ポリシーが **11 本**あり、`cond` がすべて `coach.is_owner()` になっている
- `garmin_tokens` と `app_owner` は 1 本も出てこない（クライアントから触れない）

## 3. `coach` スキーマを Data API に公開する

**これを忘れると PostgREST がスキーマを認識せず、アプリから一切読めない。**

`Settings` → `API` → **Exposed schemas** に `coach` を追加する（`public` はそのまま残す）。

## 4. 自分のアカウントを確認する

count-upper で既にアカウントがあるならそれを使う。無ければ作る。

`Authentication` → `Users` → `Add user` → `Create new user`
（**Auto Confirm User** を有効にする）

> **相乗りでは「サインアップ無効化」を主たる防御にできない。**
> count-upper 側でサインアップが開いていれば、そのアカウントで `authenticated` の
> JWT を取得できてしまうため。防御は次の 5 の `app_owner` だけである。

## 5. 所有者として登録する

`SQL Editor` で実行する。

```sql
insert into coach.app_owner (user_id)
select id from auth.users where email = 'あなたのメールアドレス';
```

確認する。

```sql
select o.user_id, u.email from coach.app_owner o join auth.users u on u.id = o.user_id;
```

**1 行返ってこなければ失敗している。** `app_owner` が空の間は `coach.is_owner()` が常に false を
返し、誰も読み書きできない（fail-closed）。

## 6. API キーを取得する

`Settings` → `API Keys`

| キー | 形式 | 用途 | 置き場 |
|---|---|---|---|
| publishable | `sb_publishable_...` | フロント | Cloudflare Pages のビルド環境変数 / `web/.env.local` |
| secret | `sb_secret_...` | バッチ | GitHub Secrets / `.env` |

`Legacy API Keys` タブの `anon` / `service_role` は**使わない**。2026 年末で廃止される。

**secret キーは RLS をバイパスする。** フロントや public なファイルに絶対に置かない。

count-upper と同じプロジェクトなのでキーも共通になる。片方が漏れたら両方に影響する。

## 7. 疎通を確認する

```bash
cd web
cp .env.example .env.local
```

`.env.local` に `VITE_SUPABASE_URL` と `VITE_SUPABASE_PUBLISHABLE_KEY` を書く。

```bash
npm run dev
```

<http://localhost:5173> を開き、4 のアカウントでログインする。

| 症状 | 原因 |
|---|---|
| ログインでき、各画面が空でエラーも出ない | 正常（データがまだ無い） |
| `permission denied for table ...` | GRANT が流れていない。0001 の末尾を再実行する |
| `The schema must be one of the following: public` | 3 の Exposed schemas に `coach` が入っていない |
| 空だが 0 件しか返らない | 5 の `app_owner` 登録を確認する |

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
