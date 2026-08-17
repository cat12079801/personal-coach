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

R4. 週あたりの実施回数の下限を確保する。週は月曜始まりで数える。
    **回数が R2 の優先度より優先される。** 優先度の高い日だけでは足りない場合、
    ポイント練習日にも置くし、休養日を使わない組み合わせも選ぶ。

    週 3 回・中 1 日だと、休養日を先に取ると間隔の制約で 2 回しか置けなくなる週がある。
    そのため置く日は総当たりで決める（候補は最大 7 日）。

## カレンダーの予定について

当初はスケート予定がある日に筋トレを削り、翌日の強度を下げる想定だった（旧ルール 2・4）。
**両方とも廃止した。** スケートと筋トレは両立してよく、翌日の調整も不要という判断のため。
「ランが休養日でスケートする日」はむしろ筋トレを置くべき日になる。

**カレンダーの予定は表示用としてそのまま載せる。ルールの判定には一切使わない。**
「今日やることを 1 画面で確認する」ためのもの。

## 実施回数の数え方

**完了記録（`strength_logs` の `program_id` 付きの行）がある日だけ数える**（2026-08-17 に変更）。

当初は「過去の `daily_menus` に何を置いたか」で数えていた。実績の入力精度に依存させない
ためだったが、置いただけでやらなかった日が実施として数えられ、翌日以降が間隔で潰れる。
「やっていないのに次が出ない」ほうが実害が大きいという判断で入れ替えた。

**記録を忘れた日はノーカウントになる**。その日はやらなかったものとして詰めて出す。
"""

from __future__ import annotations

import datetime as dt
import itertools
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
    # 過去の完了記録。{メニューの日付: 完了した program_id の集合}。
    # 実施回数と間隔の判定に使う。置いただけの日はここに現れない
    completions: dict[dt.date, set[str]]
    plan_meta: dict[str, Any] = field(default_factory=dict)
    # カレンダーの予定。表示用でありルールには使わない
    events: list[dict[str, Any]] = field(default_factory=list)


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


def _last_done(program_id: str, completions: dict[dt.date, set[str]]) -> dt.date | None:
    dates = [day for day, ids in completions.items() if program_id in ids]
    return max(dates) if dates else None


def _count_this_week(program_id: str, target: dt.date, completions: dict[dt.date, set[str]]) -> int:
    """週は月曜始まりで数える。"""
    monday = target - dt.timedelta(days=target.weekday())
    return sum(
        1 for day, ids in completions.items() if monday <= day < target and program_id in ids
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

    層ごとの貪欲法（休養日を先に全部取る）だと、間隔の制約で後続が潰れて
    回数の下限に届かなくなることがある。たとえば週 3 回・中 1 日で
    水・木(休養)・金・土・日が残っている場合、木を先に取ると木土の 2 回しか置けない。
    水金日なら 3 回置ける。

    そこで**回数を最優先**し、同数なら優先度の高い日を多く含む組を選ぶ。
    候補は最大 7 日なので総当たりで足りる。
    """
    done = _count_this_week(program.id, inp.date, inp.completions)
    remaining = program.weekly_target - done
    if remaining <= 0:
        return []

    tasks_by_date: dict[dt.date, list[PlanTask]] = {}
    for task in inp.tasks:
        tasks_by_date.setdefault(task.date, []).append(task)

    # 当日からその週の日曜まで
    sunday = inp.date + dt.timedelta(days=6 - inp.date.weekday())
    candidates = [inp.date + dt.timedelta(days=i) for i in range((sunday - inp.date).days + 1)]
    last = _last_done(program.id, inp.completions)

    def feasible(combo: tuple[dt.date, ...]) -> bool:
        placed = [d for d in [last, *combo] if d is not None]
        return all(
            abs((a - b).days) >= program.min_gap_days
            for i, a in enumerate(placed)
            for b in placed[i + 1 :]
        )

    # 置ける最大数から順に探し、見つかった時点でその数に確定する
    for size in range(min(remaining, len(candidates)), 0, -1):
        best = min(
            (combo for combo in itertools.combinations(candidates, size) if feasible(combo)),
            # 優先度の合計が小さい（休養日を多く含む）組を選び、同点なら早い日から
            key=lambda combo: (sum(_day_priority(tasks_by_date, d) for d in combo), combo),
            default=None,
        )
        if best is not None:
            return sorted(best)
    return []


def _should_place(program: Program, inp: MenuInput) -> tuple[bool, str]:
    """独自筋トレを今日置くかどうか。理由も返す。"""
    done = _count_this_week(program.id, inp.date, inp.completions)
    if program.weekly_target - done <= 0:
        return False, "weekly_target_met"

    last = _last_done(program.id, inp.completions)
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
        # ルールには使わない。当日の予定を 1 画面で見るための表示用
        "schedule": inp.events,
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
