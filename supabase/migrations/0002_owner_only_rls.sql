-- アクセスを所有者 1 人に絞る
--
-- 0001 のポリシーは `to authenticated using (true)` だった。
-- anon では読めないが、そのプロジェクトでアカウントを作れた人は全員フルアクセスになる。
-- Supabase Auth はデフォルトでサインアップが開いているため、これは穴である。
--
-- 対策は 2 段構え:
--   1. Supabase ダッシュボードで Email のサインアップを無効化する（これが主）
--   2. ポリシーを所有者の user_id に紐づける（多層防御。設定ミスで 1 が戻っても守られる）

-- ---------------------------------------------------------------------------
-- 所有者テーブル（1 行）
--   ポリシーを一つも作らない = クライアントからは読めない
-- ---------------------------------------------------------------------------
create table app_owner (
  id      smallint primary key default 1 check (id = 1),
  user_id uuid     not null unique references auth.users (id) on delete cascade
);

alter table app_owner enable row level security;

-- security definer なので RLS をバイパスして app_owner を読める
create or replace function public.is_owner() returns boolean
language sql
stable
security definer
set search_path = public, pg_temp
as $$
  select exists (select 1 from public.app_owner where user_id = auth.uid());
$$;

revoke execute on function public.is_owner() from anon;

-- ---------------------------------------------------------------------------
-- ポリシーを is_owner() ベースに張り替える
-- ---------------------------------------------------------------------------
drop policy activities_select        on activities;
drop policy running_details_select   on running_details;
drop policy daily_menus_select       on daily_menus;
drop policy bouldering_logs_all      on bouldering_logs;
drop policy strength_logs_all        on strength_logs;
drop policy skating_logs_all         on skating_logs;
drop policy push_subscriptions_all   on push_subscriptions;
drop policy notifications_select     on notifications;
drop policy notifications_update     on notifications;

-- 閲覧のみ
create policy activities_select
  on activities for select to authenticated using (public.is_owner());
create policy running_details_select
  on running_details for select to authenticated using (public.is_owner());
create policy daily_menus_select
  on daily_menus for select to authenticated using (public.is_owner());

-- 手動ログは PWA から CRUD する
create policy bouldering_logs_all
  on bouldering_logs for all to authenticated
  using (public.is_owner()) with check (public.is_owner());
create policy strength_logs_all
  on strength_logs for all to authenticated
  using (public.is_owner()) with check (public.is_owner());
create policy skating_logs_all
  on skating_logs for all to authenticated
  using (public.is_owner()) with check (public.is_owner());

-- 購読は PWA が登録・削除する（再購読のため）
create policy push_subscriptions_all
  on push_subscriptions for all to authenticated
  using (public.is_owner()) with check (public.is_owner());

-- 通知履歴は閲覧と既読更新
create policy notifications_select
  on notifications for select to authenticated using (public.is_owner());
create policy notifications_update
  on notifications for update to authenticated
  using (public.is_owner()) with check (public.is_owner());

-- ---------------------------------------------------------------------------
-- 適用後に手で 1 行入れる
--
--   insert into app_owner (user_id)
--   select id from auth.users where email = 'あなたのメールアドレス';
--
-- app_owner が空の間は is_owner() が常に false を返すため、
-- 誰も読み書きできない状態になる（fail-closed）。
-- ---------------------------------------------------------------------------
