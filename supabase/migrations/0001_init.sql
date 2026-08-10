-- personal-coach 初期スキーマ
-- 設計意図は docs/04-data-model.md を参照

create extension if not exists pgcrypto;

-- ---------------------------------------------------------------------------
-- Garmin 由来。全種目共通のサマリ
-- ---------------------------------------------------------------------------
create table activities (
  id                 uuid primary key default gen_random_uuid(),
  garmin_activity_id text        not null unique,
  sport              text        not null,          -- Garmin の activityType.typeKey
  started_at         timestamptz not null,
  duration_sec       integer,
  avg_hr             integer,
  max_hr             integer,
  calories           integer,
  -- 非公式 API はレスポンス形状が予告なく変わる。
  -- 正規化に失敗しても後から再パースできるよう生 JSON を必ず保存する
  raw                jsonb       not null,
  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now()
);

create index activities_started_at_idx on activities (started_at desc);
create index activities_sport_idx      on activities (sport);

-- ---------------------------------------------------------------------------
-- Garmin 由来。ランニングのみ
-- ---------------------------------------------------------------------------
create table running_details (
  activity_id uuid primary key references activities (id) on delete cascade,
  distance_m  numeric,
  avg_pace    numeric,      -- sec/km
  elev_gain   numeric,      -- m
  splits      jsonb,        -- 未取得なら null。2 段目ジョブで埋める
  fetched_at  timestamptz
);

-- splits 未取得のランを引くための部分インデックス（2 段ジョブ用）
create index running_details_pending_splits_idx
  on running_details (activity_id) where splits is null;

-- ---------------------------------------------------------------------------
-- 手動登録
--   activity_id は必ず NULL 許容にする。
--   ウォッチの付け忘れ・充電切れの回と、計測はしたが詳細を書かない回の
--   両方が必ず発生するため、1 対 1 必須にすると破綻する
-- ---------------------------------------------------------------------------
create table bouldering_logs (
  id          uuid primary key default gen_random_uuid(),
  activity_id uuid references activities (id) on delete set null,
  climbed_at  timestamptz not null,
  gym         text,
  sends       jsonb       not null default '[]'::jsonb,
  rpe         smallint check (rpe between 1 and 10),  -- 主観強度
  note        text,
  created_at  timestamptz not null default now()
);

create table strength_logs (
  id           uuid primary key default gen_random_uuid(),
  activity_id  uuid references activities (id) on delete set null,
  performed_at timestamptz not null,
  exercises    jsonb       not null default '[]'::jsonb,
  rpe          smallint check (rpe between 1 and 10),
  note         text,
  created_at   timestamptz not null default now()
);

create table skating_logs (
  id           uuid primary key default gen_random_uuid(),
  activity_id  uuid references activities (id) on delete set null,
  practiced_at timestamptz not null,
  elements     jsonb       not null default '[]'::jsonb,
  -- フィギュアは滑走と休憩の繰り返しで平均心拍が実感より低く出る。
  -- 負荷は心拍ではなく RPE で判断する
  rpe          smallint check (rpe between 1 and 10),
  note         text,
  created_at   timestamptz not null default now()
);

create index bouldering_logs_climbed_at_idx  on bouldering_logs (climbed_at desc);
create index strength_logs_performed_at_idx  on strength_logs   (performed_at desc);
create index skating_logs_practiced_at_idx   on skating_logs    (practiced_at desc);

create index bouldering_logs_activity_id_idx on bouldering_logs (activity_id);
create index strength_logs_activity_id_idx   on strength_logs   (activity_id);
create index skating_logs_activity_id_idx    on skating_logs    (activity_id);

-- ---------------------------------------------------------------------------
-- 生成済みメニュー
-- ---------------------------------------------------------------------------
create table daily_menus (
  date         date primary key,
  generated_at timestamptz not null default now(),
  -- 生成根拠（Garmin プラン / training_readiness / カレンダー / 適用ルール）。
  -- ルールベース生成の唯一のデバッグ手段なので必ず埋める
  source       jsonb       not null default '{}'::jsonb,
  menu         jsonb       not null,
  notified_at  timestamptz
);

-- ---------------------------------------------------------------------------
-- Web Push 購読
--   送信時に 404/410 が返ったらこの行を削除する。PWA 起動時に再購読する
-- ---------------------------------------------------------------------------
create table push_subscriptions (
  id         uuid primary key default gen_random_uuid(),
  endpoint   text        not null unique,
  p256dh     text        not null,
  auth       text        not null,
  created_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- 通知履歴（iOS では未読カウンタ・履歴一覧が必須の作りになる）
-- ---------------------------------------------------------------------------
create table notifications (
  id         uuid primary key default gen_random_uuid(),
  sent_at    timestamptz not null default now(),
  title      text        not null,
  body       text        not null,
  target_date date,                    -- 対応する daily_menus.date
  read_at    timestamptz
);

create index notifications_sent_at_idx on notifications (sent_at desc);
create index notifications_unread_idx  on notifications (sent_at desc) where read_at is null;

-- ---------------------------------------------------------------------------
-- Garmin トークン（1 行のみ）
--   クライアントには一切触らせない。RLS ポリシーを作らないことでそれを担保する
-- ---------------------------------------------------------------------------
create table garmin_tokens (
  id         smallint primary key default 1 check (id = 1),
  token_json jsonb       not null,
  updated_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- updated_at 自動更新
-- ---------------------------------------------------------------------------
create or replace function set_updated_at() returns trigger
language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger activities_set_updated_at
  before update on activities
  for each row execute function set_updated_at();

create trigger garmin_tokens_set_updated_at
  before update on garmin_tokens
  for each row execute function set_updated_at();

-- ---------------------------------------------------------------------------
-- 未紐付けの Garmin アクティビティ一覧
--   UI から詳細を追記する導線に使う
-- ---------------------------------------------------------------------------
-- security_invoker: view 経由で RLS をバイパスさせない
create view unlinked_activities with (security_invoker = true) as
  select a.*
  from activities a
  where not exists (select 1 from bouldering_logs b where b.activity_id = a.id)
    and not exists (select 1 from strength_logs   s where s.activity_id = a.id)
    and not exists (select 1 from skating_logs    k where k.activity_id = a.id);

-- ---------------------------------------------------------------------------
-- RLS
--   利用者は 1 人。バッチは service_role（RLS バイパス）、
--   フロントは anon キー + Supabase Auth のログイン済みユーザとして読む
-- ---------------------------------------------------------------------------
alter table activities         enable row level security;
alter table running_details    enable row level security;
alter table bouldering_logs    enable row level security;
alter table strength_logs      enable row level security;
alter table skating_logs       enable row level security;
alter table daily_menus        enable row level security;
alter table push_subscriptions enable row level security;
alter table notifications      enable row level security;
alter table garmin_tokens      enable row level security;
-- garmin_tokens はポリシーを一つも作らない = クライアントからは読めない

-- 閲覧のみ
create policy activities_select      on activities      for select to authenticated using (true);
create policy running_details_select on running_details for select to authenticated using (true);
create policy daily_menus_select     on daily_menus     for select to authenticated using (true);

-- 手動ログは PWA から CRUD する
create policy bouldering_logs_all on bouldering_logs for all to authenticated using (true) with check (true);
create policy strength_logs_all   on strength_logs   for all to authenticated using (true) with check (true);
create policy skating_logs_all    on skating_logs    for all to authenticated using (true) with check (true);

-- 購読は PWA が登録・削除する（再購読のため）
create policy push_subscriptions_all on push_subscriptions for all to authenticated using (true) with check (true);

-- 通知履歴は閲覧と既読更新
create policy notifications_select on notifications for select to authenticated using (true);
create policy notifications_update on notifications for update to authenticated using (true) with check (true);
