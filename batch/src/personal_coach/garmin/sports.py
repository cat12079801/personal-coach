"""Garmin の `activityType.typeKey` の分類。

PoC-2 で実データを確認した結果（docs/06-poc-notes.md）:

  running           実データで確認済み
  skating_ws        実データで確認済み（フィギュアスケート）
  strength_training 実データで確認済み
  bouldering        **未確定**。まだ記録が無い

ボルダリングはウォッチのアクティビティプロファイル次第で
bouldering / indoor_climbing / rock_climbing / floor_climbing のどれかになる。
どれが来ても同じ扱いにする。
"""

from __future__ import annotations

from typing import Any

RUNNING: frozenset[str] = frozenset(
    {
        "running",
        "trail_running",
        "street_running",
        "track_running",
        "treadmill_running",
        "indoor_running",
        "virtual_run",
        "ultra_run",
        "obstacle_run",
    }
)

CLIMBING: frozenset[str] = frozenset(
    {"bouldering", "indoor_climbing", "rock_climbing", "floor_climbing"}
)

SKATING: frozenset[str] = frozenset({"skating_ws"})

STRENGTH: frozenset[str] = frozenset({"strength_training"})

# 取り込まない種目。
# 歩行は日常的な活動であり、トレーニングとして扱わない。
IGNORED: frozenset[str] = frozenset({"walking", "casual_walking", "speed_walking", "hiking"})

# 主観強度（RPE / Feel）を詳細から取りに行く種目。
#
# 当初はクライミング系とスケート（心拍が当てにならない種目）を対象にしていたが、
# 毎回 Garmin Connect で入力する手間に見合わないため**ランのみ**に変更した。
# その結果、クライミング系とスケートには負荷指標が無くなる（心拍も RPE も使えない）。
# これらは「記録するが負荷は評価しない」種目として扱う。
NEEDS_RPE: frozenset[str] = RUNNING

# 心拍ベースの負荷指標に混ぜてはいけない種目。
#   クライミング: ホールドを握る動作で前腕が緊張し、腕を上げた状態が続く
#   スケート:     滑走と休憩の繰り返しで平均心拍が実感より低く出る
# docs/01-overview.md の「心拍の扱いに関する注意」を参照。
HR_UNRELIABLE: frozenset[str] = CLIMBING | SKATING


def sport_of(activity: dict[str, Any]) -> str:
    return (activity.get("activityType") or {}).get("typeKey") or "unknown"


def is_running(sport: str) -> bool:
    return sport in RUNNING


def is_ignored(sport: str) -> bool:
    return sport in IGNORED


def needs_detail(sport: str) -> bool:
    return sport in NEEDS_RPE
