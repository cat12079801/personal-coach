"""バッチのエントリポイント。GitHub Actions から呼ぶ。

pc-ingest   03:00 JST — 取り込み + メニュー生成
pc-notify   08:00 JST — 生成済みメニューの通知
"""

from __future__ import annotations

import datetime as dt
import logging
import sys

JST = dt.timezone(dt.timedelta(hours=9))


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def today_jst() -> dt.date:
    return dt.datetime.now(JST).date()


def ingest() -> int:
    _setup_logging()
    from .ingest import ingest_activities, ingest_pending_splits

    count = ingest_activities()
    splits = ingest_pending_splits()
    logging.info("取り込み完了: activities=%d splits=%d", count, splits)

    # TODO(マイルストーン 6): メニュー生成を呼ぶ
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
