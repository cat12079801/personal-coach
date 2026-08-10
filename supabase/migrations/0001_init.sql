-- personal-coach 初期スキーマ
-- 設計意図は docs/04-data-model.md を参照
--
-- 無料プランのプロジェクト数上限のため、既存プロジェクト（count-upper）に相乗りする。
-- 相手の public スキーマと混ざらないよう、専用の coach スキーマに全部入れる。
-- 詳細は docs/09-setup-supabase.md。

create schema if not exists coach;

-- gen_random_uuid() は PostgreSQL 13 以降 core に入っているので拡張は要らない

-- ---------------------------------------------------------------------------
-- Garmin 由来。全種目共通のサマリ
-- ---------------------------------------------------------------------------
create table coach.activities (
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

create index activities_started_at_idx on coach.activities (started_at desc);
create index activities_sport_idx      on coach.activities (sport);

-- ---------------------------------------------------------------------------
-- Garmin 由来。ランニングのみ
-- ---------------------------------------------------------------------------
create table coach.running_details (
  activity_id uuid primary key references coach.activities (id) on delete cascade,
  distance_m  numeric,
  avg_pace    numeric,      -- sec/km
  elev_gain   numeric,      -- m
  splits      jsonb,        -- 未取得なら null。2 段目ジョブで埋める
  fetched_at  timestamptz
);

-- splits 未取得のランを引くための部分インデックス（2 段ジョブ用）
create index running_details_pending_splits_idx
  on coach.running_details (activity_id) where splits is null;

-- ---------------------------------------------------------------------------
-- 手動登録
--   activity_id は必ず NULL 許容にする。
--   ウォッチの付け忘れ・充電切れの回と、計測はしたが詳細を書かない回の
--   両方が必ず発生するため、1 対 1 必須にすると破綻する
-- ---------------------------------------------------------------------------
create table coach.bouldering_logs (
  id          uuid primary key default gen_random_uuid(),
  activity_id uuid references coach.activities (id) on delete set null,
  climbed_at  timestamptz not null,
  gym         text,
  sends       jsonb       not null default '[]'::jsonb,
  rpe         smallint check (rpe between 1 and 10),  -- 主観強度
  note        text,
  created_at  timestamptz not null default now()
);

create table coach.strength_logs (
  id           uuid primary key default gen_random_uuid(),
  activity_id  uuid references coach.activities (id) on delete set null,
  performed_at timestamptz not null,
  exercises    jsonb       not null default '[]'::jsonb,
  rpe          smallint check (rpe between 1 and 10),
  note         text,
  created_at   timestamptz not null default now()
);

create table coach.skating_logs (
  id           uuid primary key default gen_random_uuid(),
  activity_id  uuid references coach.activities (id) on delete set null,
  practiced_at timestamptz not null,
  elements     jsonb       not null default '[]'::jsonb,
  -- フィギュアは滑走と休憩の繰り返しで平均心拍が実感より低く出る。
  -- 負荷は心拍ではなく RPE で判断する
  rpe          smallint check (rpe between 1 and 10),
  note         text,
  created_at   timestamptz not null default now()
);

create index bouldering_logs_climbed_at_idx  on coach.bouldering_logs (climbed_at desc);
create index strength_logs_performed_at_idx  on coach.strength_logs   (performed_at desc);
create index skating_logs_practiced_at_idx   on coach.skating_logs    (practiced_at desc);

create index bouldering_logs_activity_id_idx on coach.bouldering_logs (activity_id);
create index strength_logs_activity_id_idx   on coach.strength_logs   (activity_id);
create index skating_logs_activity_id_idx    on coach.skating_logs    (activity_id);

-- ---------------------------------------------------------------------------
-- 生成済みメニュー
-- ---------------------------------------------------------------------------
create table coach.daily_menus (
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
create table coach.push_subscriptions (
  id         uuid primary key default gen_random_uuid(),
  endpoint   text        not null unique,
  p256dh     text        not null,
  auth       text        not null,
  created_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- 通知履歴（iOS では未読カウンタ・履歴一覧が必須の作りになる）
-- ---------------------------------------------------------------------------
create table coach.notifications (
  id          uuid primary key default gen_random_uuid(),
  sent_at     timestamptz not null default now(),
  title       text        not null,
  body        text        not null,
  target_date date,                   -- 対応する coach.daily_menus.date
  read_at     timestamptz
);

create index notifications_sent_at_idx on coach.notifications (sent_at desc);
create index notifications_unread_idx  on coach.notifications (sent_at desc) where read_at is null;

-- ---------------------------------------------------------------------------
-- Garmin トークン（1 行のみ）
--   クライアントには一切触らせない。RLS ポリシーも GRANT も与えないことで担保する
-- ---------------------------------------------------------------------------
create table coach.garmin_tokens (
  id         smallint primary key default 1 check (id = 1),
  token_json jsonb       not null,
  updated_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- updated_at 自動更新
-- ---------------------------------------------------------------------------
create or replace function coach.set_updated_at() returns trigger
language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger activities_set_updated_at
  before update on coach.activities
  for each row execute function coach.set_updated_at();

create trigger garmin_tokens_set_updated_at
  before update on coach.garmin_tokens
  for each row execute function coach.set_updated_at();

-- ---------------------------------------------------------------------------
-- 未紐付けの Garmin アクティビティ一覧
--   UI から詳細を追記する導線に使う
--   security_invoker: view 経由で RLS をバイパスさせない
-- ---------------------------------------------------------------------------
create view coach.unlinked_activities with (security_invoker = true) as
  select a.*
  from coach.activities a
  where not exists (select 1 from coach.bouldering_logs b where b.activity_id = a.id)
    and not exists (select 1 from coach.strength_logs   s where s.activity_id = a.id)
    and not exists (select 1 from coach.skating_logs    k where k.activity_id = a.id);

-- ---------------------------------------------------------------------------
-- RLS
--   利用者は 1 人。バッチは secret key（service_role ロール。RLS バイパス）、
--   フロントは publishable key + Supabase Auth のログイン済みユーザとして読む
-- ---------------------------------------------------------------------------
alter table coach.activities         enable row level security;
alter table coach.running_details    enable row level security;
alter table coach.bouldering_logs    enable row level security;
alter table coach.strength_logs      enable row level security;
alter table coach.skating_logs       enable row level security;
alter table coach.daily_menus        enable row level security;
alter table coach.push_subscriptions enable row level security;
alter table coach.notifications      enable row level security;
alter table coach.garmin_tokens      enable row level security;
-- garmin_tokens はポリシーを一つも作らない = クライアントからは読めない

-- ポリシーの条件は 0002 で is_owner() に張り替える。
-- ここでは「認証済みなら可」の暫定条件で作る（0002 を必ず続けて流すこと）
create policy activities_select      on coach.activities      for select to authenticated using (true);
create policy running_details_select on coach.running_details for select to authenticated using (true);
create policy daily_menus_select     on coach.daily_menus     for select to authenticated using (true);

create policy bouldering_logs_all on coach.bouldering_logs for all to authenticated using (true) with check (true);
create policy strength_logs_all   on coach.strength_logs   for all to authenticated using (true) with check (true);
create policy skating_logs_all    on coach.skating_logs    for all to authenticated using (true) with check (true);

create policy push_subscriptions_all on coach.push_subscriptions for all to authenticated using (true) with check (true);

create policy notifications_select on coach.notifications for select to authenticated using (true);
create policy notifications_update on coach.notifications for update to authenticated using (true) with check (true);

-- ---------------------------------------------------------------------------
-- Data API ロールへの権限付与
--
-- Supabase の新しい既定（auto_expose_new_tables 無効）では、マイグレーションで作成した
-- テーブルは明示的な GRANT がないと PostgREST 経由で一切アクセスできず、
-- 「permission denied for table」になる。RLS ポリシーだけでは足りない。
--
-- anon にはテーブル権限を与えない（未認証アクセスをテーブルレベルでも遮断する多層防御）。
-- garmin_tokens はどのロールにも与えない。バッチは service_role で触る。
-- ---------------------------------------------------------------------------
grant usage on schema coach to anon, authenticated, service_role;

grant select on coach.activities         to authenticated;
grant select on coach.running_details    to authenticated;
grant select on coach.daily_menus        to authenticated;
grant select on coach.unlinked_activities to authenticated;

grant select, insert, update, delete on coach.bouldering_logs    to authenticated;
grant select, insert, update, delete on coach.strength_logs      to authenticated;
grant select, insert, update, delete on coach.skating_logs       to authenticated;
grant select, insert, update, delete on coach.push_subscriptions to authenticated;

grant select, update on coach.notifications to authenticated;

grant all on all tables in schema coach to service_role;
