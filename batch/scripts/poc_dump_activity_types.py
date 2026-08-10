#!/usr/bin/env python
"""PoC-2: ボルダリング / フィギュアスケートが Garmin 上でどの type_key になるかを調べる。

    cd batch
    uv run python scripts/poc_dump_activity_types.py

type_key は機種と設定に依存する。実機で確認すること。
結果を docs/06-poc-notes.md の表に記入する。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from personal_coach.garmin.auth import garmin_session  # noqa: E402

OUT_DIR = Path(__file__).resolve().parents[1] / ".poc-out"
KEYWORDS = ("run", "skat", "climb", "boulder", "strength", "ice")


def main() -> int:
    with garmin_session() as g:
        types = g.get_activity_types()
        # 直近の実アクティビティがどの typeKey で入っているかも見る
        recent = g.get_activities(start=0, limit=30)

    OUT_DIR.mkdir(exist_ok=True)
    (OUT_DIR / "activity_types.json").write_text(
        json.dumps(types, ensure_ascii=False, indent=2, default=str)
    )
    (OUT_DIR / "recent_activities.json").write_text(
        json.dumps(recent, ensure_ascii=False, indent=2, default=str)
    )

    print("== 関連しそうな type_key ==")
    for t in types:
        key = str(t.get("typeKey", ""))
        if any(k in key.lower() for k in KEYWORDS):
            print(f"  {t.get('typeId')}\t{key}")

    print("\n== 直近アクティビティの typeKey ==")
    seen: dict[str, int] = {}
    for a in recent:
        key = str(a.get("activityType", {}).get("typeKey", "?"))
        seen[key] = seen.get(key, 0) + 1
    for key, count in sorted(seen.items(), key=lambda x: -x[1]):
        print(f"  {key}\t{count} 件")

    print(f"\n出力先: {OUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
