-- 独自に足す筋トレのプログラム
--
-- Garmin コーチの筋トレは「ランのための補強」に閉じている（自重・アクティベーション・
-- コアスタビリティ）。目的が違うので、上半身とスキル系を別枠で足す（OD-5・案 C）。
--
-- **段階の中身は本人が定義する。** アプリは段階を保持して出す機構だけを持つ。
-- プランシェやシンピ倒立の進行内容をアプリ側が決めることはしない。

create table coach.strength_programs (
  id            uuid     primary key default gen_random_uuid(),
  name          text     not null,                       -- 'プランシェ' 'シンピ倒立' '腕立て伏せ'
  -- 現在の段階。stages の添字（1 始まり）。手動で上げ下げする（OD-5）
  stage         smallint not null default 1 check (stage >= 1),
  -- 段階の定義。[{"label": "タックプランシェ 10 秒", "sets": 3, "note": ""}, ...]
  stages        jsonb    not null default '[]'::jsonb,
  weekly_target smallint not null default 2 check (weekly_target between 1 and 7),
  -- 前回実施日との日数差の下限。2 なら「中 1 日以上」
  min_gap_days  smallint not null default 2 check (min_gap_days >= 1),
  sort_order    smallint not null default 0,
  active        boolean  not null default true,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);

create index strength_programs_active_idx on coach.strength_programs (sort_order)
  where active;

create trigger strength_programs_set_updated_at
  before update on coach.strength_programs
  for each row execute function coach.set_updated_at();

alter table coach.strength_programs enable row level security;

create policy strength_programs_all
  on coach.strength_programs for all to authenticated
  using (coach.is_owner()) with check (coach.is_owner());

grant select, insert, update, delete on coach.strength_programs to authenticated;
grant all on coach.strength_programs to service_role;
