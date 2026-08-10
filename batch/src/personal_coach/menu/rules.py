"""メニュー生成（マイルストーン 6・未着手）。

**ルールベースで実装する。LLM は使わない。**

入力が 3 つとも揃うまで書かない:
  - Garmin コーチのランニングプラン（PoC-1 で取得元 API と形状を確定させる）
  - training_readiness
  - Google カレンダー（スケート予定の有無）

## 適用ルール

1. Garmin コーチのランニングプランを最優先し、その内容は改変しない
2. スケートの予定有無は Google カレンダーを参照して判定する
3. ランがポイント練習の日は筋トレを入れない、休養/イージーの日は筋トレを差し込む
4. スケート予定がある日は筋トレを削り、翌日の強度を下げる
5. training_readiness が低い日は全体の強度を 1 段下げる

ルール 4 は「翌日」に影響するため、当日分だけを見る純関数にはならない。
前日の生成結果（daily_menus.source）を入力に含める設計にする。

## 生成根拠を必ず残す

`daily_menus.source` に「使ったプラン」「readiness の値」「カレンダーの予定」
「適用したルール一覧」を入れる。ルールベース生成の唯一のデバッグ手段になる。
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MenuInput:
    """メニュー生成の入力。フィールドは PoC-1 の結果に合わせて確定させる。"""

    date: dt.date
    garmin_plan: dict[str, Any] | None
    training_readiness: dict[str, Any] | None
    has_skating: bool
    previous_source: dict[str, Any] | None = None


@dataclass
class MenuOutput:
    menu: dict[str, Any]
    source: dict[str, Any] = field(default_factory=dict)


def generate(inp: MenuInput) -> MenuOutput:
    raise NotImplementedError(
        "PoC-1 で Garmin コーチのプランの形状を確定させてから実装する（docs/06-poc-notes.md）"
    )
