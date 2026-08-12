"""Garmin アクティビティの取り込み。

正規化に使うフィールドは PoC-2 で実データを確認済み（docs/06-poc-notes.md）。

取り込みは 3 段構え。1 回の実行で全部やるが、それぞれ独立して再実行できる。

  1. サマリ  : 差分同期して activities に upsert。raw を必ず保存する
  2. splits  : ランのうち splits 未取得のものだけ追う
  3. 詳細    : ランの RPE / Feel を取る（一覧には入らないため）

2 と 3 を分けているのは、1 件ごとに API を叩く必要があり、初回バックフィルで
まとめてやると Garmin のレート制限に当たるため。1 回の実行で追う件数に上限を設ける。
"""

from __future__ import annotations

import datetime as dt
import logging
from typing import Any

from .db import client, known_activity_ids
from .garmin import sports
from .garmin.auth import garmin_session
from .garmin.sync import fetch_detail, fetch_new_activities, fetch_splits

logger = logging.getLogger(__name__)

# 1 回の実行で追う 2 段目・3 段目の件数。残りは次回の実行で埋める
SPLITS_PER_RUN = 20
DETAILS_PER_RUN = 20

# RPE は後から Garmin Connect で入力するものなので、一度取っただけでは拾えない。
# 直近この日数以内で rpe が未設定のものは取り直す。
DETAIL_REFRESH_DAYS = 14


def _int(value: Any) -> int | None:
    return None if value is None else int(value)


def _to_utc_iso(value: str | None) -> str | None:
    """`startTimeGMT` は "2026-08-10 22:51:34" 形式の素の文字列で返る。"""
    if not value:
        return None
    return dt.datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=dt.UTC).isoformat()


def _normalize(activity: dict[str, Any]) -> dict[str, Any]:
    """Garmin のアクティビティ JSON を activities 行に落とす。

    正規化に失敗しても raw さえ入っていれば後から復旧できる（docs/04-data-model.md）。
    そのため、取れないフィールドは None にして落とさない。
    """
    return {
        "garmin_activity_id": str(activity["activityId"]),
        "sport": sports.sport_of(activity),
        "started_at": _to_utc_iso(activity.get("startTimeGMT")),
        "duration_sec": _int(activity.get("duration")),
        "avg_hr": _int(activity.get("averageHR")),
        "max_hr": _int(activity.get("maxHR")),
        "calories": _int(activity.get("calories")),
        "raw": activity,
    }


def _running_detail_row(activity: dict[str, Any], activity_id: str) -> dict[str, Any]:
    """averageSpeed は m/s。avg_pace は sec/km に直して持つ。"""
    speed = activity.get("averageSpeed")
    return {
        "activity_id": activity_id,
        "distance_m": activity.get("distance"),
        "avg_pace": (1000 / speed) if speed else None,
        "elev_gain": activity.get("elevationGain"),
    }


def ingest_activities(max_pages: int | None = None) -> int:
    """アクティビティを取り込む。取り込んだ件数を返す。

    max_pages を指定するとバックフィルモードになる。

    通常（max_pages=None）は差分同期。新しい順に取得し、既知 ID に当たったら打ち切る。
    日次の取り込みはこれでよい。

    ただし差分同期では**過去へ遡れない**。1 件目が既知なら即座に打ち切るためである。
    そこで max_pages を指定した場合は既知 ID による打ち切りをやめ、
    指定ページ数ぶんを頭から舐め直す。upsert なので重複しても害はない。
    さらに古い履歴が欲しければページ数を増やす。
    """
    backfill = max_pages is not None
    known = set() if backfill else known_activity_ids()
    if backfill:
        logger.info("バックフィルモード（%d ページ = 最大 %d 件）", max_pages, max_pages * 50)

    with garmin_session() as garmin:
        activities = fetch_new_activities(garmin, known, max_pages=max_pages)

    # 歩行などトレーニングとして扱わない種目は保存しない
    ignored = [a for a in activities if sports.is_ignored(sports.sport_of(a))]
    if ignored:
        logger.info("対象外の種目を %d 件スキップした", len(ignored))
    activities = [a for a in activities if not sports.is_ignored(sports.sport_of(a))]

    logger.info("取り込み対象 %d 件", len(activities))
    if not activities:
        return 0

    rows = [_normalize(a) for a in activities]
    client().table("activities").upsert(rows, on_conflict="garmin_activity_id").execute()

    # ラン種目は running_details の行を作る。splits は 2 段目で埋める
    running = [a for a in activities if sports.is_running(sports.sport_of(a))]
    if running:
        ids = _activity_id_map(str(a["activityId"]) for a in running)
        detail_rows = [
            _running_detail_row(a, ids[str(a["activityId"])])
            for a in running
            if str(a["activityId"]) in ids
        ]
        client().table("running_details").upsert(detail_rows, on_conflict="activity_id").execute()
        logger.info("running_details %d 件", len(detail_rows))

    return len(rows)


def _activity_id_map(garmin_ids: Any) -> dict[str, str]:
    """garmin_activity_id -> activities.id"""
    res = (
        client()
        .table("activities")
        .select("id, garmin_activity_id")
        .in_("garmin_activity_id", list(garmin_ids))
        .execute()
    )
    return {row["garmin_activity_id"]: row["id"] for row in res.data}


def ingest_pending_splits(limit: int = SPLITS_PER_RUN) -> int:
    """splits 未取得のランを追う。取得件数を返す。"""
    res = (
        client()
        .table("running_details")
        .select("activity_id, activities(garmin_activity_id)")
        .is_("splits", "null")
        .limit(limit)
        .execute()
    )
    if not res.data:
        return 0

    now = dt.datetime.now(dt.UTC).isoformat()
    with garmin_session() as garmin:
        for row in res.data:
            garmin_id = row["activities"]["garmin_activity_id"]
            splits = fetch_splits(garmin, garmin_id)
            client().table("running_details").update({"splits": splits, "fetched_at": now}).eq(
                "activity_id", row["activity_id"]
            ).execute()

    logger.info("splits %d 件", len(res.data))
    return len(res.data)


def ingest_pending_details(limit: int = DETAILS_PER_RUN) -> int:
    """ランの詳細（RPE / Feel）を追う。取得件数を返す。

    対象は次のいずれか。
      - 一度も詳細を取っていない
      - 直近 DETAIL_REFRESH_DAYS 日以内で rpe が未設定（後から入力された可能性がある）
    """
    since = (dt.datetime.now(dt.UTC) - dt.timedelta(days=DETAIL_REFRESH_DAYS)).isoformat()
    res = (
        client()
        .table("activities")
        .select("id, garmin_activity_id, sport")
        .in_("sport", sorted(sports.NEEDS_RPE))
        .or_(f"detail_fetched_at.is.null,and(rpe.is.null,started_at.gte.{since})")
        .order("started_at", desc=True)
        .limit(limit)
        .execute()
    )
    if not res.data:
        return 0

    now = dt.datetime.now(dt.UTC).isoformat()
    with garmin_session() as garmin:
        for row in res.data:
            detail = fetch_detail(garmin, row["garmin_activity_id"])
            summary = detail.get("summaryDTO") or {}
            # directWorkoutRpe / directWorkoutFeel はいずれも 0-100 スケール。
            # RPE は見慣れた 0-10 に直して持つ
            rpe = summary.get("directWorkoutRpe")
            client().table("activities").update(
                {
                    "rpe": round(rpe / 10) if rpe is not None else None,
                    "feel": _int(summary.get("directWorkoutFeel")),
                    "detail_raw": detail,
                    "detail_fetched_at": now,
                }
            ).eq("id", row["id"]).execute()

    logger.info("詳細 %d 件", len(res.data))
    return len(res.data)
