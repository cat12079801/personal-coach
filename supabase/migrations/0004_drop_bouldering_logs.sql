-- ボルダリングの手動ログを廃止する
--
-- ボルダリングは Garmin Connect 側でアクティビティとして記録する方針に変更した。
-- したがって coach.bouldering_logs は不要。取り込みバッチ経由で coach.activities に入る。
--
-- 注意: 心拍の扱いは変わらない。ボルダリングの手首光学式心拍は信用できない
-- （ホールドを握る動作で前腕が緊張し、腕を上げた状態が続くため）。
-- 心拍ベースの負荷指標にボルダリングを混ぜないこと（docs/01-overview.md）。

-- unlinked_activities が bouldering_logs を参照しているので先に差し替える。
-- 列構成は変わらないので create or replace でよい。
create or replace view coach.unlinked_activities with (security_invoker = true) as
  select a.*
  from coach.activities a
  where not exists (select 1 from coach.strength_logs s where s.activity_id = a.id)
    and not exists (select 1 from coach.skating_logs  k where k.activity_id = a.id);

-- ポリシー・インデックス・GRANT はテーブルと一緒に落ちる
drop table coach.bouldering_logs;
