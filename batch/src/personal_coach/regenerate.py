"""メニュー再生成リクエストの処理。

PWA の「メニューを再生成」ボタンは `regenerate_requests` に 1 行積むだけで、
それを拾う側を持たなかった（独自バックエンドを作らないため）。ここがその拾う側で、
15 分おきの `regenerate.yml` から呼ばれる（docs/08-open-decisions.md OD-1）。

**再生成では Garmin を必ず引き直す。**

Garmin のアダプティブコーチは睡眠スコアや training_readiness を見て当日のプランを
差し替えることがある。03:00 の取り込みは就寝中の値で組むため、日中に見ている
メニューが最新とは限らない。したがって再生成は DB の値からの組み直しではなく、
`build_menu()` を通してプランと readiness をその時点で取得し直す。
"""

from __future__ import annotations

import datetime as dt
import logging
from typing import Any

from .db import client
from .menu.build import build_menu

logger = logging.getLogger(__name__)

JST = dt.timezone(dt.timedelta(hours=9))


def _pending() -> list[dict[str, Any]]:
    res = (
        client()
        .table("regenerate_requests")
        .select("id, target_date")
        .is_("processed_at", "null")
        .order("requested_at")
        .execute()
    )
    return res.data or []


def _finish(ids: list[str], result: str) -> None:
    client().table("regenerate_requests").update(
        {"processed_at": dt.datetime.now(dt.UTC).isoformat(), "result": result}
    ).in_("id", ids).execute()


def process_requests() -> int:
    """未処理のリクエストを拾ってメニューを作り直す。再生成した日数を返す。

    Garmin を叩くのは作り直す日ぶんだけ。未処理が無ければ Supabase を 1 回引いて終わる。
    """
    pending = _pending()
    if not pending:
        logger.info("未処理のリクエストは無い")
        return 0

    by_date: dict[str, list[str]] = {}
    for row in pending:
        by_date.setdefault(row["target_date"], []).append(row["id"])

    # 作り直すのは当日ぶんだけ。taskList は当日以降しか返さず、
    # 過ぎた日を引き直しても意味が無い（溜まった古い行で Garmin を叩かないため）
    today = dt.datetime.now(JST).date()
    stale = [i for date, ids in by_date.items() if date != today.isoformat() for i in ids]
    if stale:
        _finish(stale, "skipped: 当日以外")
        logger.info("当日以外のリクエスト %d 件を破棄した", len(stale))

    ids = by_date.get(today.isoformat())
    if not ids:
        return 0

    # 同じ日に複数積まれていても Garmin は 1 回だけ引く
    menu = build_menu(today)
    _finish(ids, f"ok: {menu['summary']}")
    logger.info("%s を再生成した（リクエスト %d 件）", today, len(ids))
    return 1
