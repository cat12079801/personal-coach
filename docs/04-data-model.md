# 04. データモデル

初期案。実 DDL は [supabase/migrations/0001_init.sql](../supabase/migrations/0001_init.sql)。

```sql
-- Garmin 由来。全種目共通のサマリ
activities (
  id, garmin_activity_id unique, sport, started_at,
  duration_sec, avg_hr, max_hr, calories,
  raw jsonb  -- 取得した JSON をそのまま保存
)

-- Garmin 由来。ランニングのみ
running_details (activity_id fk, distance_m, avg_pace, elev_gain, splits jsonb)

-- 手動登録。activity_id は NULL 許容（必須）
bouldering_logs (id, activity_id fk null, climbed_at, gym, sends jsonb, note)
strength_logs  (id, activity_id fk null, performed_at, exercises jsonb, note)
skating_logs   (id, activity_id fk null, practiced_at, elements jsonb, note)

daily_menus        (date pk, generated_at, source jsonb, menu jsonb, notified_at)
push_subscriptions (id, endpoint unique, p256dh, auth, created_at)
garmin_tokens      (id pk, token_json jsonb, updated_at)
```

## 設計上の必須ポイント

### 手動ログの `activity_id` は必ず NULL 許容にする

ウォッチの付け忘れ・充電切れの回と、計測はしたが詳細を書かない回の**両方が必ず発生する**。
1 対 1 必須にすると破綻する。

### `raw jsonb` を必ず保存する

非公式 API はレスポンス形状が予告なく変わるため、正規化に失敗しても後から再パースできるように
しておく。取り込み時点で正規化に失敗しても、`raw` さえ入っていれば復旧できる。

### 未紐付けアクティビティの導線

UI には「**未紐付けの Garmin アクティビティ一覧**」を出し、そこから詳細を追記する導線を作る。

```sql
select a.* from activities a
left join bouldering_logs b on b.activity_id = a.id
left join strength_logs   s on s.activity_id = a.id
left join skating_logs    k on k.activity_id = a.id
where b.id is null and s.id is null and k.id is null;
```

## jsonb カラムの想定形状

いずれも手動登録なので自分で決めてよい。以下は初期案であり、UI 実装時に確定させる。

```jsonc
// bouldering_logs.sends
[{ "grade": "3級", "wall": "スラブ", "attempts": 3, "sent": true }]

// strength_logs.exercises
[{ "name": "腕立て伏せ", "sets": [{ "reps": 20 }, { "reps": 18 }] },
 { "name": "デッドリフト", "sets": [{ "reps": 8, "weight_kg": 80 }] }]

// skating_logs.elements
[{ "name": "シングルアクセル", "attempts": 10, "success": 4, "note": "" }]

// daily_menus.source  — 生成の根拠。後から「なぜこのメニューになったか」を追える
{ "garmin_plan": {}, "training_readiness": 62, "calendar": [], "applied_rules": ["..."] }

// daily_menus.menu
{ "run": {}, "strength": [], "summary": "イージー 40 分 + 体幹" }
```

`daily_menus.source` に生成根拠を残すのは必須。ルールベース生成の唯一のデバッグ手段になる。

## RLS 方針

利用者は 1 人。**「認証済みなら誰でも」ではなく「所有者本人だけ」に絞る。**

- **バッチ**は secret key（`sb_secret_...`）で書き込む。Postgres の `service_role` ロールに
  対応し BYPASSRLS を持つため RLS を素通りする
- **フロント**は publishable key（`sb_publishable_...`）+ Supabase Auth のログイン済みユーザ
  として読む。Postgres の `anon` / `authenticated` ロールで動くので RLS が効く
- 旧 `anon` / `service_role` の JWT キーでも動くが、2026 年末で廃止予定なので使わない
- `anon` にはポリシーを一つも作らない → 未ログインでは何も読めない
- ポリシーの条件は `public.is_owner()`。`app_owner` テーブルの 1 行に登録した `user_id` と
  `auth.uid()` が一致する場合のみ true を返す
- **`garmin_tokens` と `app_owner` はクライアントから一切触らせない**（ポリシーを一つも作らない）

### なぜ `using (true)` ではだめか

`to authenticated using (true)` だと、**そのプロジェクトでアカウントを作れた人は全員フルアクセス**
になる。Supabase Auth はデフォルトでサインアップが開いているため、これは穴になる。

対策は 2 段構え。片方だけに頼らない。

1. **Supabase ダッシュボードで Email のサインアップを無効化する**（主たる防御）
2. **ポリシーを `is_owner()` に紐づける**（多層防御。設定が戻っても守られる）

### fail-closed

`app_owner` が空の間は `is_owner()` が常に false を返し、誰も読み書きできない。
マイグレーション適用直後は必ずこの状態になるので、下記の 1 行を手で入れる。

```sql
insert into app_owner (user_id)
select id from auth.users where email = 'あなたのメールアドレス';
```
