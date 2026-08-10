# ADR-0006: 既存プロジェクトに `coach` スキーマで相乗りする

- 状態: 採用
- 日付: 2026-08-10

## 背景

Supabase の無料プランは **1 ユーザあたり 2 プロジェクトまで**（管理者・オーナーになっている
全 organization を横断した上限）。既に 2 つ使っており、新規作成できなかった。
新しい organization を作っても回避できない。

## 決定

既存プロジェクト（[count-upper](https://github.com/cat12079801/count-upper) が使っているもの）に
**専用スキーマ `coach` を切って相乗りする。**

count-upper は本アプリが動けば不要になる見込みであり、相乗りは恒久構成ではない。

## 却下した選択肢

### 既存プロジェクトを pause する

無料のまま枠を空けられるが、count-upper がまだ現役である。

### Pro にする（$25/mo）

個人用アプリ 1 個のために払う額として釣り合わない。

### 相手の `public` スキーマに同居する

テーブル名の衝突は今のところ無い（`counters` / `count_logs`）が、
どちらのテーブルか判別できなくなり、count-upper を畳むときに切り分けられない。

## 帰結

### スキーマを明示しないと動かない

クライアント側で必ず `coach` を指定する。忘れると相手の `public` を見に行って 404 になる。

```ts
createClient(url, key, { db: { schema: 'coach' } })
```

```python
create_client(url, key, options=ClientOptions(schema="coach"))
```

ダッシュボードの `Settings > API` で **Exposed schemas に `coach` を追加**する必要もある。
これを忘れると PostgREST がスキーマを認識しない。

### GRANT が必須

Supabase の新しい既定（`auto_expose_new_tables` 無効）では、マイグレーションで作成した
テーブルは明示的な GRANT がないと PostgREST 経由で
「permission denied for table」になる。RLS ポリシーだけでは足りない。

`anon` にはテーブル権限を与えない（未認証アクセスをテーブルレベルでも遮断する多層防御）。
`garmin_tokens` と `app_owner` はどのロールにも与えない。

### Auth を共用する

**これが相乗りの最大の注意点である。** count-upper 側でサインアップが開いていれば、
そのアカウントで `authenticated` の JWT を取得できてしまう。

したがって「サインアップ無効化」は主たる防御として使えない。
**`coach.is_owner()` によるポリシー側の絞り込みが唯一の防御になる。**
[ADR-0005](0005-garmin-token-in-supabase.md) と [0002 のマイグレーション](../../supabase/migrations/0002_owner_only_rls.sql)
を崩さないこと。

検証は Postgres 16 で実施済み。別アカウントの JWT では 0 件、`app_owner` が空なら本人でも 0 件、
`garmin_tokens` / `app_owner` は `authenticated` から permission denied になることを確認した。

### 将来 count-upper を畳むとき

`coach` スキーマに閉じているので、`public` 側を落とすだけでよい。
専用プロジェクトへ移すなら `pg_dump --schema=coach` で持ち出せる。
