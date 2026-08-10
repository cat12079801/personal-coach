-- メニュー再生成のリクエスト
--
-- .ics は Google 側でキャッシュされ、反映が数時間遅れることがある。
-- 前夜遅くに追加した予定を 03:00 のバッチが拾えないため、
-- PWA から再生成を依頼できるようにする（docs/adr/0003-ical-instead-of-oauth.md）。
--
-- 独自バックエンドは持たないので、PWA は「依頼を 1 行入れる」ところまでしかやらない。
-- これを誰が拾うかは未決定。docs/08-open-decisions.md を参照。

create table coach.regenerate_requests (
  id           uuid primary key default gen_random_uuid(),
  target_date  date        not null,
  requested_at timestamptz not null default now(),
  processed_at timestamptz,
  result       text
);

-- 未処理のリクエストだけを引くための部分インデックス
create index regenerate_requests_pending_idx
  on coach.regenerate_requests (requested_at) where processed_at is null;

alter table coach.regenerate_requests enable row level security;

-- 依頼の作成と自分の依頼の確認のみ。更新はバッチ（service_role）が行う
create policy regenerate_requests_insert
  on coach.regenerate_requests for insert to authenticated with check (coach.is_owner());
create policy regenerate_requests_select
  on coach.regenerate_requests for select to authenticated using (coach.is_owner());

grant select, insert on coach.regenerate_requests to authenticated;
grant all on coach.regenerate_requests to service_role;
