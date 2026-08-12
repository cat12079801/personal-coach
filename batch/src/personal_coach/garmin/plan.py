"""Garmin コーチのプラン取得。

形状は PoC-1 で実データを確認済み（docs/06-poc-notes.md）。

  get_training_plans()                      → 有効なプランを選ぶ
  get_adaptive_training_plan_by_id(plan_id) → taskList（当日から 7 日ぶん）

`get_training_plan_by_id()` はアダプティブプランには使えない（400 Not a phased plan）。
`get_scheduled_workouts()` は月カレンダーのビューで強度も休養日も入らないため使わない。
"""

from __future__ import annotations

import datetime as dt
import logging
from typing import Any

from .sync import with_backoff

logger = logging.getLogger(__name__)

ADAPTIVE_CATEGORY = "FBT_ADAPTIVE"
ACTIVE_STATUS = "Scheduled"


def active_plan(client: Any) -> dict[str, Any] | None:
    """有効なアダプティブプランを 1 つ返す。無ければ None。"""
    plans = with_backoff(client.get_training_plans) or {}
    candidates = [
        p
        for p in plans.get("trainingPlanList") or []
        if p.get("trainingPlanCategory") == ADAPTIVE_CATEGORY
        and (p.get("trainingStatus") or {}).get("statusKey") == ACTIVE_STATUS
    ]
    if not candidates:
        logger.warning("有効なアダプティブプランが見つからない")
        return None
    if len(candidates) > 1:
        logger.warning("有効なプランが %d 個ある。最初のものを使う", len(candidates))
    return candidates[0]


def _current_phase(plan: dict[str, Any]) -> str | None:
    for phase in plan.get("adaptivePlanPhases") or []:
        if phase.get("currentPhase"):
            return phase.get("trainingPhase")
    return None


def fetch_plan_tasks(
    client: Any, plan: dict[str, Any] | None
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """プランの taskList を正規化した dict のリストにして返す。メタ情報も返す。

    ここで menu 側の型に変換しないのは、garmin パッケージが menu に依存しないため
    （Garmin 依存はこのパッケージに閉じ込める。docs/02-architecture.md）。
    """
    if plan is None:
        return [], {}

    plan_id = plan["trainingPlanId"]
    detail = with_backoff(lambda: client.get_adaptive_training_plan_by_id(plan_id)) or {}

    tasks: list[dict[str, Any]] = []
    for task in detail.get("taskList") or []:
        workout = task.get("taskWorkout") or {}
        date = task.get("calendarDate")
        if not date:
            continue
        tasks.append(
            {
                "date": dt.date.fromisoformat(date),
                "sport": (workout.get("sportType") or {}).get("sportTypeKey"),
                "name": workout.get("workoutName"),
                "duration_sec": workout.get("estimatedDurationInSecs"),
                "intensity": workout.get("trainingEffectLabel"),
                "rest_day": bool(workout.get("restDay")),
            }
        )

    meta = {
        "plan_id": plan_id,
        "name": detail.get("name") or plan.get("name"),
        "phase": _current_phase(detail) or _current_phase(plan),
        "end_date": (detail.get("endDate") or plan.get("endDate") or "")[:10] or None,
    }
    logger.info("プラン %s の taskList %d 件", meta["name"], len(tasks))
    return tasks, meta


def fetch_readiness(client: Any, target: dt.date) -> dict[str, Any] | None:
    """training_readiness は要素 1 個のリストを返す（PoC-1）。"""
    result = with_backoff(lambda: client.get_training_readiness(target.isoformat()))
    if isinstance(result, list):
        return result[0] if result else None
    return result or None
