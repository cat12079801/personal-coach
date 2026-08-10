-- アクセスを所有者 1 人に絞る
--
-- 0001 のポリシーは `to authenticated using (true)` だった。
-- anon では読めないが、そのプロジェクトでアカウントを作れた人は全員フルアクセスになる。
--
-- **相乗り先（count-upper）とは Auth を共用する。** 相手側でサインアップが開いていれば、
-- そのアカウントで authenticated の JWT を取得できてしまう。
-- したがってサインアップ無効化に頼りきらず、ポリシー側で所有者に絞ることが必須になる。

-- ---------------------------------------------------------------------------
-- 所有者テーブル（1 行）
--   ポリシーも GRANT も与えない = クライアントからは読めない
-- ---------------------------------------------------------------------------
create table coach.app_owner (
  id      smallint primary key default 1 check (id = 1),
  user_id uuid     not null unique references auth.users (id) on delete cascade
);

alter table coach.app_owner enable row level security;

-- security definer なので RLS をバイパスして app_owner を読める
create or replace function coach.is_owner() returns boolean
language sql
stable
security definer
set search_path = coach, pg_temp
as $$
  select exists (select 1 from coach.app_owner where user_id = auth.uid());
$$;

grant execute on function coach.is_owner() to authenticated, service_role;
revoke execute on function coach.is_owner() from anon;

-- ---------------------------------------------------------------------------
-- ポリシーを is_owner() ベースに張り替える
-- ---------------------------------------------------------------------------
drop policy activities_select        on coach.activities;
drop policy running_details_select   on coach.running_details;
drop policy daily_menus_select       on coach.daily_menus;
drop policy bouldering_logs_all      on coach.bouldering_logs;
drop policy strength_logs_all        on coach.strength_logs;
drop policy skating_logs_all         on coach.skating_logs;
drop policy push_subscriptions_all   on coach.push_subscriptions;
drop policy notifications_select     on coach.notifications;
drop policy notifications_update     on coach.notifications;

-- 閲覧のみ
create policy activities_select
  on coach.activities for select to authenticated using (coach.is_owner());
create policy running_details_select
  on coach.running_details for select to authenticated using (coach.is_owner());
create policy daily_menus_select
  on coach.daily_menus for select to authenticated using (coach.is_owner());

-- 手動ログは PWA から CRUD する
create policy bouldering_logs_all
  on coach.bouldering_logs for all to authenticated
  using (coach.is_owner()) with check (coach.is_owner());
create policy strength_logs_all
  on coach.strength_logs for all to authenticated
  using (coach.is_owner()) with check (coach.is_owner());
create policy skating_logs_all
  on coach.skating_logs for all to authenticated
  using (coach.is_owner()) with check (coach.is_owner());

-- 購読は PWA が登録・削除する（再購読のため）
create policy push_subscriptions_all
  on coach.push_subscriptions for all to authenticated
  using (coach.is_owner()) with check (coach.is_owner());

-- 通知履歴は閲覧と既読更新
create policy notifications_select
  on coach.notifications for select to authenticated using (coach.is_owner());
create policy notifications_update
  on coach.notifications for update to authenticated
  using (coach.is_owner()) with check (coach.is_owner());

-- ---------------------------------------------------------------------------
-- 適用後に手で 1 行入れる
--
--   insert into coach.app_owner (user_id)
--   select id from auth.users where email = 'あなたのメールアドレス';
--
-- app_owner が空の間は is_owner() が常に false を返すため、
-- 誰も読み書きできない状態になる（fail-closed）。
-- ---------------------------------------------------------------------------
