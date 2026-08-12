"""メニュー生成。

**ルールベースで実装する。LLM は使わない。**

出力の構造:

    今日のメニュー
    ├── ラン          ← Garmin のプランをそのまま。改変しない
    ├── 補強(Garmin)  ← Garmin が置いた筋トレ。そのまま
    └── 独自筋トレ     ← アプリが足す。上半身・スキル系

## ルール（2026-08-12 に本人レビュー済み）

R1. **Garmin のプランは改変しない。** 絶対条件。ランと Garmin の補強は取得したまま出す。

R2. 独自筋トレを置く日。**優先度は 休養日 > ポイント練習でない日 > ポイント練習日**。
    Garmin の補強がある日に重ねてよい。

    `taskList` は当日から 7 日ぶん返るので、**その週の残りを先読みして置く日を決める**。
    日次で手前から貪欲に置くと、直後に休養日があっても中 N 日の制約で弾かれ、
    「基本は休養日に置く」という意図から外れるため。

R3. training_readiness が低い日は**セット数を減らす**（段階は下げない）。
    `level` が LOW / VERY_LOW、または `score < 50`。
    ただし `validSleep: false` の日は score が当てにならないので下げない。
    **ランには手を入れない**（R1）。

R4. 週あたりの実施回数の下限を確保する。既定は週 2 回・中 1 日以上（`min_gap_days=2`）。
    優先度の高い日だけでは回数が足りない場合、ポイント練習日にも置く。
    週は月曜始まりで数える。

## スケートについて

当初はスケート予定がある日に筋トレを削り、翌日の強度を下げる想定だった（旧ルール 2・4）。
**両方とも廃止した。** スケートと筋トレは両立してよく、翌日の調整も不要という判断のため。
「ランが休養日でスケートする日」はむしろ筋トレを置くべき日になる。

結果として、この生成ロジックは Google カレンダーを参照しない。

## 実施回数の数え方

実績（`strength_logs` や Garmin の記録）ではなく、**過去の `daily_menus` に何を置いたか**で数える。
実績の入力精度に依存させないため。
"""

from __future__ import annotations

import datetime as dt
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ポイント練習とみなす強度ラベル（docs/06-poc-notes.md の PoC-1）
HARD_LABELS: frozenset[str] = frozenset({"ANAEROBIC_CAPACITY", "LACTATE_THRESHOLD"})

LOW_READINESS_LEVELS: frozenset[str] = frozenset({"LOW", "VERY_LOW"})
LOW_READINESS_SCORE = 50


@dataclass(frozen=True)
class PlanTask:
    """`taskList` の 1 件を正規化したもの。"""

    date: dt.date
    sport: str | None
    name: str | None
    duration_sec: int | None
    intensity: str | None
    rest_day: bool

    @property
    def is_running(self) -> bool:
        return self.sport == "running"

    @property
    def is_strength(self) -> bool:
        return self.sport == "strength_training"

    @property
    def is_hard(self) -> bool:
        return self.intensity in HARD_LABELS


@dataclass(frozen=True)
class Program:
    """独自筋トレ 1 種目。"""

    id: str
    name: str
    stage: int
    stages: list[dict[str, Any]]
    weekly_target: int
    min_gap_days: int

    def current(self) -> dict[str, Any] | None:
        index = self.stage - 1
        return self.stages[index] if 0 <= index < len(self.stages) else None


@dataclass(frozen=True)
class MenuInput:
    date: dt.date
    tasks: list[PlanTask]
    readiness: dict[str, Any] | None
    programs: list[Program]
    # 過去の daily_menus。{date: menu} 形式。実施回数と間隔の判定に使う
    recent_menus: dict[dt.date, dict[str, Any]]
    plan_meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class MenuOutput:
    menu: dict[str, Any]
    source: dict[str, Any]


def _low_readiness(readiness: dict[str, Any] | None) -> bool:
    if not readiness:
        return False
    if not readiness.get("validSleep", True):
        # 睡眠が取れていないと score が当てにならない
        return False
    if readiness.get("level") in LOW_READINESS_LEVELS:
        return True
    score = readiness.get("score")
    return score is not None and score < LOW_READINESS_SCORE


def _last_done(program_id: str, recent: dict[dt.date, dict[str, Any]]) -> dt.date | None:
    dates = [
        day
        for day, menu in recent.items()
        if any(item.get("program_id") == program_id for item in menu.get("own_strength") or [])
    ]
    return max(dates) if dates else None


def _count_this_week(
    program_id: str, target: dt.date, recent: dict[dt.date, dict[str, Any]]
) -> int:
    """週は月曜始まりで数える。"""
    monday = target - dt.timedelta(days=target.weekday())
    return sum(
        1
        for day, menu in recent.items()
        if monday <= day < target
        and any(item.get("program_id") == program_id for item in menu.get("own_strength") or [])
    )


# 置く日の優先度。小さいほど優先
_PRIORITY_REST = 0
_PRIORITY_NORMAL = 1
_PRIORITY_HARD = 2


def _day_priority(tasks_by_date: dict[dt.date, list[PlanTask]], day: dt.date) -> int:
    tasks = tasks_by_date.get(day) or []
    if tasks and all(t.rest_day for t in tasks):
        return _PRIORITY_REST
    if any(t.is_running and t.is_hard for t in tasks):
        return _PRIORITY_HARD
    # プラン外の日（taskList の窓を越えた先）は通常日とみなす
    return _PRIORITY_NORMAL


def _plan_days(program: Program, inp: MenuInput) -> list[dt.date]:
    """その週の残りから、この種目を置く日を選ぶ。

    優先度（休養日 > 通常日 > ポイント練習日）の順に、間隔の制約を守りながら
    必要回数ぶんだけ選ぶ。当日より前は既に確定しているので触らない。
    """
    done = _count_this_week(program.id, inp.date, inp.recent_menus)
    remaining = program.weekly_target - done
    if remaining <= 0:
        return []

    tasks_by_date: dict[dt.date, list[PlanTask]] = {}
    for task in inp.tasks:
        tasks_by_date.setdefault(task.date, []).append(task)

    # 当日からその週の日曜まで
    sunday = inp.date + dt.timedelta(days=6 - inp.date.weekday())
    candidates = [inp.date + dt.timedelta(days=i) for i in range((sunday - inp.date).days + 1)]

    last = _last_done(program.id, inp.recent_menus)
    chosen: list[dt.date] = []
    # 優先度の高い層から順に埋める。同じ層の中では日付の早い順
    for priority in (_PRIORITY_REST, _PRIORITY_NORMAL, _PRIORITY_HARD):
        for day in candidates:
            if len(chosen) >= remaining:
                break
            if day in chosen or _day_priority(tasks_by_date, day) != priority:
                continue
            # 既に置いた日（前週ぶんを含む）との間隔を確認する
            placed = [d for d in [last, *chosen] if d is not None]
            if any(abs((day - d).days) < program.min_gap_days for d in placed):
                continue
            chosen.append(day)
        if len(chosen) >= remaining:
            break
    return sorted(chosen)


def _should_place(program: Program, inp: MenuInput) -> tuple[bool, str]:
    """独自筋トレを今日置くかどうか。理由も返す。"""
    done = _count_this_week(program.id, inp.date, inp.recent_menus)
    if program.weekly_target - done <= 0:
        return False, "weekly_target_met"

    last = _last_done(program.id, inp.recent_menus)
    if last is not None and (inp.date - last).days < program.min_gap_days:
        return False, "min_gap"

    planned = _plan_days(program, inp)
    if inp.date in planned:
        return True, "planned"
    if planned:
        return False, f"deferred_to_{planned[0].isoformat()}"
    return False, "no_slot"


def generate(inp: MenuInput) -> MenuOutput:
    today = [t for t in inp.tasks if t.date == inp.date]
    run = next((t for t in today if t.is_running), None)
    garmin_strength = [t for t in today if t.is_strength]
    rest_day = bool(today) and all(t.rest_day for t in today)
    is_hard_day = run is not None and run.is_hard

    low = _low_readiness(inp.readiness)
    applied: list[str] = []
    if rest_day:
        applied.append("R2:rest_day")
    if is_hard_day:
        applied.append("R2:hard_day")
    if low:
        applied.append("R3:low_readiness")

    own: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    for program in inp.programs:
        place, reason = _should_place(program, inp)
        decisions.append({"program": program.name, "placed": place, "reason": reason})
        if not place:
            continue
        stage = program.current()
        if stage is None:
            logger.warning("%s の段階 %d が定義されていない", program.name, program.stage)
            continue
        sets = stage.get("sets")
        # R3: 段階は下げず、セット数だけ減らす
        if low and isinstance(sets, int) and sets > 1:
            sets -= 1
        own.append(
            {
                "program_id": program.id,
                "program": program.name,
                "stage": program.stage,
                "label": stage.get("label"),
                "sets": sets,
                "note": stage.get("note"),
            }
        )

    menu = {
        "summary": _summarize(run, garmin_strength, own, rest_day=rest_day),
        "rest_day": rest_day,
        "run": _task_dict(run),
        "garmin_strength": [_task_dict(t) for t in garmin_strength],
        "own_strength": own,
    }
    source = {
        "plan": inp.plan_meta,
        "readiness": inp.readiness,
        "tasks": [_task_dict(t) for t in today],
        "applied_rules": applied,
        "program_decisions": decisions,
    }
    return MenuOutput(menu=menu, source=source)


def _task_dict(task: PlanTask | None) -> dict[str, Any] | None:
    if task is None:
        return None
    return {
        "sport": task.sport,
        "name": task.name,
        "duration_sec": task.duration_sec,
        "intensity": task.intensity,
        "rest_day": task.rest_day,
    }


def _minutes(seconds: int | None) -> str:
    return f"{round(seconds / 60)} 分" if seconds else ""


def _summarize(
    run: PlanTask | None,
    garmin_strength: list[PlanTask],
    own: list[dict[str, Any]],
    *,
    rest_day: bool,
) -> str:
    parts: list[str] = []
    if run is not None:
        parts.append(f"{run.name} {_minutes(run.duration_sec)}".strip())
    elif rest_day:
        parts.append("ランは休養")
    parts += [t.name for t in garmin_strength if t.name]
    parts += [item["program"] for item in own]
    return " + ".join(p for p in parts if p) or "予定なし"
