"""メニュー生成の入力を集めて DB に保存する。

ルール自体は rules.py（純粋関数）。ここは入出力だけを担当する。
"""

from __future__ import annotations

import datetime as dt
import logging
from typing import Any

from ..db import client
from ..garmin.auth import garmin_session
from ..garmin.plan import active_plan, fetch_plan_tasks, fetch_readiness
from .rules import MenuInput, PlanTask, Program, generate

logger = logging.getLogger(__name__)

JST = dt.timezone(dt.timedelta(hours=9))

# 実施回数と間隔の判定に使う遡り日数
LOOKBACK_DAYS = 14


def _load_programs() -> list[Program]:
    res = (
        client()
        .table("strength_programs")
        .select("*")
        .eq("active", True)
        .order("sort_order")
        .execute()
    )
    return [
        Program(
            id=row["id"],
            name=row["name"],
            stage=row["stage"],
            stages=row["stages"] or [],
            weekly_target=row["weekly_target"],
            min_gap_days=row["min_gap_days"],
        )
        for row in res.data
    ]


def _load_recent_menus(target: dt.date) -> dict[dt.date, dict[str, Any]]:
    since = (target - dt.timedelta(days=LOOKBACK_DAYS)).isoformat()
    res = (
        client()
        .table("daily_menus")
        .select("date, menu")
        .gte("date", since)
        .lt("date", target.isoformat())
        .execute()
    )
    return {dt.date.fromisoformat(row["date"]): row["menu"] or {} for row in res.data}


def build_menu(target: dt.date | None = None) -> dict[str, Any]:
    """当日のメニューを生成して daily_menus に保存する。"""
    target = target or dt.datetime.now(JST).date()

    with garmin_session() as garmin:
        plan = active_plan(garmin)
        tasks, plan_meta = fetch_plan_tasks(garmin, plan)
        readiness = fetch_readiness(garmin, target)

    result = generate(
        MenuInput(
            date=target,
            tasks=[PlanTask(**t) for t in tasks],
            readiness=readiness,
            programs=_load_programs(),
            recent_menus=_load_recent_menus(target),
            plan_meta=plan_meta,
        )
    )

    client().table("daily_menus").upsert(
        {
            "date": target.isoformat(),
            "generated_at": dt.datetime.now(dt.UTC).isoformat(),
            "menu": result.menu,
            "source": result.source,
        },
        on_conflict="date",
    ).execute()

    logger.info("%s のメニューを生成した: %s", target, result.menu["summary"])
    return result.menu
