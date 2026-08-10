#!/usr/bin/env python
"""PoC-1: Garmin コーチのプランがどの API から取得できるかを調べる使い捨てスクリプト。

    cd batch
    uv run python scripts/poc_dump_training_plans.py

生 JSON を `batch/.poc-out/` に書き出す（gitignore 済み）。**個人データなのでコミットしない。**
目視で確認した結果を docs/06-poc-notes.md に記録すること。

確認したいこと:
  - コーチ（アダプティブプラン）の当日ワークアウトはどれで取れるか
  - ワークアウトの構造（ウォームアップ / インターバル / クールダウン）
  - 「ポイント練習 / イージー / 休養」を判定できるフィールド
  - training_readiness のスコア範囲と「低い」の閾値
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from personal_coach.garmin.auth import garmin_session  # noqa: E402

OUT_DIR = Path(__file__).resolve().parents[1] / ".poc-out"


def dump(name: str, value: object) -> None:
    OUT_DIR.mkdir(exist_ok=True)
    path = OUT_DIR / f"{name}.json"
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str))
    size = path.stat().st_size
    print(f"  -> {path.name} ({size:,} bytes)")


def try_dump(name: str, fn) -> object | None:
    print(f"[{name}]")
    try:
        value = fn()
    except Exception as e:  # noqa: BLE001 - どのメソッドが生きているかを知るのが目的
        print(f"  !! {type(e).__name__}: {e}")
        return None
    dump(name, value)
    return value


def main() -> int:
    today = dt.date.today().isoformat()
    year, month = dt.date.today().year, dt.date.today().month

    with garmin_session() as g:
        plans = try_dump("training_plans", g.get_training_plans)
        try_dump("scheduled_workouts", lambda: g.get_scheduled_workouts(year, month))
        try_dump("training_status", lambda: g.get_training_status(today))
        try_dump("training_readiness", lambda: g.get_training_readiness(today))
        try_dump("race_predictions", g.get_race_predictions)

        # プラン ID が取れたら個別も引く。レスポンス形状が不明なので緩く探す
        for plan_id in _extract_ids(plans):
            try_dump(f"training_plan_{plan_id}", lambda i=plan_id: g.get_training_plan_by_id(i))
            try_dump(
                f"adaptive_plan_{plan_id}",
                lambda i=plan_id: g.get_adaptive_training_plan_by_id(i),
            )

    print(f"\n出力先: {OUT_DIR}")
    print("結果の要点を docs/06-poc-notes.md に記録すること")
    return 0


def _extract_ids(plans: object) -> list[str]:
    """プラン一覧から ID らしきものを拾う。形状が不明なので総当たりで探す。"""
    found: list[str] = []
    stack: list[object] = [plans]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            for key, value in node.items():
                if "id" in key.lower() and isinstance(value, (int, str)):
                    found.append(str(value))
                else:
                    stack.append(value)
        elif isinstance(node, list):
            stack.extend(node)
    return list(dict.fromkeys(found))[:5]


if __name__ == "__main__":
    sys.exit(main())
