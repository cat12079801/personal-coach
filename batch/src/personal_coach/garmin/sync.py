"""Garmin からの差分同期。

新しい順に取得し、既知の activityId に当たったら打ち切る。
初回バックフィルでは既知 ID が空なので全件を舐めることになる。429 対策のスリープを入れる。
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any

from garminconnect import GarminConnectTooManyRequestsError

logger = logging.getLogger(__name__)

PAGE_SIZE = 50
PAGE_INTERVAL_SEC = 1.0  # 初回バックフィル時に Garmin を叩き続けないための間隔


def with_backoff[T](fn: Callable[[], T], *, attempts: int = 5, base_sec: float = 5.0) -> T:
    """429 を握って指数バックオフする。"""
    for i in range(attempts):
        try:
            return fn()
        except GarminConnectTooManyRequestsError:
            if i == attempts - 1:
                raise
            wait = base_sec * (2**i)
            logger.warning(
                "429 を受信した。%.0f 秒待機して再試行する (%d/%d)", wait, i + 1, attempts
            )
            time.sleep(wait)
    raise AssertionError("unreachable")


def fetch_new_activities(client: Any, known_ids: set[str]) -> list[dict[str, Any]]:
    """既知 ID に当たるまで新しい順に取得する。"""
    fetched: list[dict[str, Any]] = []
    start = 0
    while True:
        batch = with_backoff(lambda s=start: client.get_activities(start=s, limit=PAGE_SIZE))
        if not batch:
            return fetched
        for activity in batch:
            if str(activity["activityId"]) in known_ids:
                return fetched
            fetched.append(activity)
        start += PAGE_SIZE
        time.sleep(PAGE_INTERVAL_SEC)


def fetch_splits(client: Any, garmin_activity_id: str) -> dict[str, Any]:
    """ランの splits を取得する。サマリ取り込みとは別ジョブで呼ぶ。"""
    return with_backoff(lambda: client.get_activity_splits(garmin_activity_id))
