"""バッチのエントリポイント。GitHub Actions から呼ぶ。

pc-ingest   03:00 JST — 取り込み + メニュー生成
pc-notify   08:00 JST — 生成済みメニューの通知
"""

from __future__ import annotations

import datetime as dt
import logging
import os
import sys

JST = dt.timezone(dt.timedelta(hours=9))


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def today_jst() -> dt.date:
    return dt.datetime.now(JST).date()


def _max_pages() -> int | None:
    """workflow_dispatch の入力。無検証でそのまま使わず、必ず int に落とす。"""
    raw = (os.environ.get("BACKFILL_PAGES") or "").strip()
    if not raw:
        return None
    try:
        value = int(raw)
    except ValueError:
        logging.warning("BACKFILL_PAGES が数値でないので無視する")
        return None
    return value if value > 0 else None


def ingest() -> int:
    _setup_logging()
    from .ingest import ingest_activities, ingest_pending_details, ingest_pending_splits

    count = ingest_activities(max_pages=_max_pages())
    splits = ingest_pending_splits()
    details = ingest_pending_details()
    logging.info("取り込み完了: activities=%d splits=%d details=%d", count, splits, details)

    from .menu.build import build_menu

    build_menu()
    return 0


def notify() -> int:
    _setup_logging()
    from .db import client
    from .push.sender import send_menu_notification

    target = today_jst().isoformat()
    res = client().table("daily_menus").select("*").eq("date", target).execute()
    if not res.data:
        logging.warning("%s のメニューが生成されていない。通知をスキップする", target)
        return 0

    menu = res.data[0]
    summary = menu["menu"].get("summary", "本日のメニュー")
    send_menu_notification(title="今日のトレーニング", summary=summary, target_date=target)
    client().table("daily_menus").update({"notified_at": "now()"}).eq("date", target).execute()
    return 0


if __name__ == "__main__":
    sys.exit(ingest())
