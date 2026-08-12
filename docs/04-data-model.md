# 04. データモデル

初期案。実 DDL は [supabase/migrations/0001_init.sql](../supabase/migrations/0001_init.sql)。

既存プロジェクトに相乗りしているため、**全テーブルは `coach` スキーマに置く**
（[ADR-0006](adr/0006-share-existing-supabase-project.md)）。以下では `coach.` を省略する。

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
-- strength_logs の program_id / menu_date は「メニューから完了にした行」の目印（0007）
strength_logs  (id, activity_id fk null, performed_at, exercises jsonb, note,
                program_id fk null, menu_date null)
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

### 独自筋トレの完了は `strength_logs` に入れる

専用テーブルを作らない。手動登録と同じ場所に入れておけば履歴が 1 本にまとまり、
未紐付け一覧から Garmin アクティビティに後付けで紐付ける導線もそのまま使える。

- `program_id` と `menu_date` が入っている行 = メニューの「完了にする」で作られた行
- 両方 `null` の行 = `/logs` で自由入力した行

`(menu_date, program_id)` に部分 UNIQUE を張って二重記録を防ぐ。取り消しは行の削除。

**実績はメニューと独立に持つ。** メニューの「3 セット」「15 秒キープ」は目標であって
実績ではないため、完了を押した時点では**セット数ぶんの空枠だけ**を作り、数値は入れない。
レップ数・秒数・セット数は後からいつでも編集できる（`planned_sets` は提示された値の控えで、
実績を変えても書き換えない）。

**この記録はメニュー生成のルールには影響しない。** 実施回数と間隔の判定は
過去の `daily_menus` に何を置いたかで数える（[rules.py](../batch/src/personal_coach/menu/rules.py)）。
実績の入力精度に依存させないため。

### 未紐付けアクティビティの導線

UI には「**未紐付けの Garmin アクティビティ一覧**」を出し、そこから詳細を追記する導線を作る。

```sql
select a.* from activities a
left join strength_logs s on s.activity_id = a.id
left join skating_logs  k on k.activity_id = a.id
where s.id is null and k.id is null;
```

## jsonb カラムの想定形状

いずれも手動登録なので自分で決めてよい。以下は初期案であり、UI 実装時に確定させる。

**`strength_logs.exercises` には 2 種類の形が入る。** 読む側は両方を許容すること。

```jsonc
// strength_logs.exercises — /logs の自由入力（FIELDS が実体。OD-3）
[{ "name": "腕立て伏せ", "sets": [{ "reps": 20 }, { "reps": 18 }] },
 { "name": "デッドリフト", "sets": [{ "reps": 8, "weight_kg": 80 }] }]

// strength_logs.exercises — メニューから完了にした行（要素は常に 1 個）
// unit がレップと秒を切り替える。プランシェ等のキープ系は秒で数える
[{ "name": "タックプランシェ 15 秒キープ", "stage": 5, "unit": "seconds",
   "planned_sets": 3,                                  // メニューの提示。書き換えない
   "sets": [{ "value": 15 }, { "value": 12 }] }]        // 実績。後から編集する

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
- **`garmin_tokens` と `app_owner` はクライアントから一切触らせない**
  （ポリシーも GRANT も与えない）

### RLS だけでは足りない — GRANT が要る

Supabase の新しい既定（`auto_expose_new_tables` 無効）では、マイグレーションで作成した
テーブルは明示的な GRANT がないと PostgREST 経由で「permission denied for table」になる。

`anon` にはテーブル権限を与えない。未認証アクセスをテーブルレベルでも遮断する多層防御。

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
