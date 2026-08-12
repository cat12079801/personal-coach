-- Garmin アクティビティの主観強度
--
-- PoC-2 で確認した（docs/06-poc-notes.md）:
--   get_activities()（一覧）には主観系のフィールドが無い。
--   get_activity(id)（詳細）の summaryDTO.directWorkoutFeel / directWorkoutRpe にある。
--   いずれも 0-100 スケール。
--
-- 心拍が当てにならない種目（クライミング系・スケート）の負荷判定に使う。
-- 詳細は 2 段目ジョブで取りに行く。ラン splits と同じ枠組み。

alter table coach.activities
  add column rpe               smallint check (rpe between 0 and 10),   -- 0-100 を 10 で割った値
  add column feel              smallint check (feel between 0 and 100), -- 0-100 のまま
  add column detail_raw        jsonb,                                   -- get_activity() の生 JSON
  add column detail_fetched_at timestamptz;

-- 詳細が未取得のものを引くための部分インデックス（2 段ジョブ用）
create index activities_pending_detail_idx
  on coach.activities (started_at desc) where detail_fetched_at is null;
