"""Garmin アクティビティの取り込み（マイルストーン 3・未着手）。

**正規化はまだ書かない。**
`get_activities()` のレスポンス形状は PoC-1 / PoC-2 で実データをダンプして確認してから
`_normalize()` を実装する（docs/06-poc-notes.md）。推測で書くと必ず作り直しになる。

取り込みの流れ:
  1. 既知の garmin_activity_id を DB から引く
  2. 新しい順に取得し、既知 ID に当たったら打ち切る（garmin.sync.fetch_new_activities）
  3. raw をそのまま入れつつ upsert する
  4. ラン種目は running_details の行を splits=null で作る
  5. splits 未取得のランだけを別ジョブで追う（2 段ジョブ）
"""

from __future__ import annotations

import logging
from typing import Any

from .db import client, known_activity_ids
from .garmin.auth import garmin_session
from .garmin.sync import fetch_new_activities, fetch_splits

logger = logging.getLogger(__name__)


def _normalize(activity: dict[str, Any]) -> dict[str, Any]:
    """Garmin のアクティビティ JSON を activities 行に落とす。

    PoC でダンプした実データを見てから実装すること。
    どのフィールドが sport / started_at / duration_sec / avg_hr / max_hr / calories に
    対応するかは機種と設定に依存するため、ここを推測で書かない。
    """
    raise NotImplementedError("PoC-1 / PoC-2 の結果を docs/06-poc-notes.md に記録してから実装する")


def _is_running(row: dict[str, Any]) -> bool:
    """ラン種目か。type_key は PoC-2 で確定させる。"""
    raise NotImplementedError("PoC-2 で type_key を確定させてから実装する")


def ingest_activities() -> int:
    """新規アクティビティを取り込む。取り込んだ件数を返す。"""
    known = known_activity_ids()
    with garmin_session() as garmin:
        activities = fetch_new_activities(garmin, known)

    logger.info("新規アクティビティ %d 件", len(activities))
    if not activities:
        return 0

    rows = [_normalize(a) for a in activities]
    client().table("activities").upsert(rows, on_conflict="garmin_activity_id").execute()

    running = [r for r in rows if _is_running(r)]
    if running:
        ids = _activity_ids_for(r["garmin_activity_id"] for r in running)
        client().table("running_details").upsert(
            [{"activity_id": i} for i in ids], on_conflict="activity_id"
        ).execute()

    return len(rows)


def _activity_ids_for(garmin_ids: Any) -> list[str]:
    res = (
        client()
        .table("activities")
        .select("id")
        .in_("garmin_activity_id", list(garmin_ids))
        .execute()
    )
    return [row["id"] for row in res.data]


def ingest_pending_splits(limit: int = 20) -> int:
    """splits 未取得のランを追う 2 段目ジョブ。取得件数を返す。"""
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

    with garmin_session() as garmin:
        for row in res.data:
            garmin_id = row["activities"]["garmin_activity_id"]
            splits = fetch_splits(garmin, garmin_id)
            client().table("running_details").update({"splits": splits, "fetched_at": "now()"}).eq(
                "activity_id", row["activity_id"]
            ).execute()

    return len(res.data)
