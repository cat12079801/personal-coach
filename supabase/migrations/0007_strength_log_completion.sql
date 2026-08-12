-- メニューの独自筋トレを「完了」として記録できるようにする
--
-- 記録先は新しいテーブルではなく既存の coach.strength_logs にする。
-- 手動登録（/logs）と同じ場所に入れておけば履歴が 1 本にまとまり、
-- 未紐付け一覧から Garmin アクティビティに後付けで紐付ける導線もそのまま使える。
--
-- program_id / menu_date が入っている行が「メニューから完了にした行」、
-- 両方 null の行が「/logs で自由入力した行」になる。
--
-- **この記録はメニュー生成のルールには影響しない。** 実施回数と間隔の判定は
-- 過去の daily_menus に何を置いたかで数える（batch/src/personal_coach/menu/rules.py）。
-- 実績の入力精度に依存させないため（OD-5）。

alter table coach.strength_logs
  -- 種目が消えても履歴は残す。種目名は exercises jsonb 側にも入れてある
  add column program_id uuid references coach.strength_programs (id) on delete set null,
  -- 対応する coach.daily_menus.date。performed_at とは別に持つ。
  -- 深夜にこなした回を「その日のメニューの完了」として扱うため
  add column menu_date  date;

-- 同じ日・同じ種目を二重に記録させない。UI のトグルの冪等性をここで担保する
create unique index strength_logs_menu_program_key
  on coach.strength_logs (menu_date, program_id)
  where program_id is not null;

create index strength_logs_menu_date_idx
  on coach.strength_logs (menu_date desc) where menu_date is not null;
