"""Google カレンダーの非公開 iCal URL を読む。

OAuth もサービスアカウントも使わない（docs/adr/0003-ical-instead-of-oauth.md）。

## 用途

**当日の予定を表示するためだけに使う。メニュー生成のルールには影響させない。**

当初はスケート予定の有無で筋トレの出し入れを判定する想定だったが、そのルールは廃止した
（スケートと筋トレは両立してよい）。現在は「今日やることを 1 画面で確認する」ための
表示用データとして扱う。

## 注意

この .ics は Google 側でキャッシュされ、反映が数時間遅れることがある。
前夜遅くに追加した予定を 03:00 のバッチが拾えないため、
アプリ側の「メニュー再生成」ボタンでの手動リカバリとセットで運用する。
"""

from __future__ import annotations

import datetime as dt
import logging
from dataclasses import dataclass
from typing import Any

import requests
from icalendar import Calendar

from .config import calendar_ics_url

logger = logging.getLogger(__name__)

TIMEOUT_SEC = 30
JST = dt.timezone(dt.timedelta(hours=9))


@dataclass(frozen=True)
class Event:
    summary: str
    start: dt.datetime | dt.date
    end: dt.datetime | dt.date | None

    @property
    def all_day(self) -> bool:
        return not isinstance(self.start, dt.datetime)

    @property
    def date(self) -> dt.date:
        """JST での日付。終日予定はそのまま日付として扱う。"""
        if isinstance(self.start, dt.datetime):
            start = self.start
            if start.tzinfo is None:
                start = start.replace(tzinfo=dt.UTC)
            return start.astimezone(JST).date()
        return self.start

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "start": self.start.isoformat(),
            "end": self.end.isoformat() if self.end else None,
            "all_day": self.all_day,
        }


def fetch_events(target: dt.date) -> list[Event]:
    """指定日（JST）の予定を返す。

    繰り返し予定の展開はしていない。必要になったら `recurring-ical-events` を入れる。
    """
    # URL は認証情報相当。例外メッセージにも載せない
    try:
        res = requests.get(calendar_ics_url(), timeout=TIMEOUT_SEC)
        res.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"カレンダーの取得に失敗した: {type(e).__name__}") from None

    events: list[Event] = []
    for component in Calendar.from_ical(res.content).walk("VEVENT"):
        start_prop = component.get("DTSTART")
        if start_prop is None:
            continue
        end_prop = component.get("DTEND")
        event = Event(
            summary=str(component.get("SUMMARY", "")),
            start=start_prop.dt,
            end=end_prop.dt if end_prop else None,
        )
        if event.date == target:
            events.append(event)

    events.sort(key=lambda e: (e.all_day is False, str(e.start)))
    logger.info("%s の予定 %d 件", target, len(events))
    return events


def fetch_events_safe(target: dt.date) -> list[dict[str, Any]]:
    """取得に失敗しても空リストを返す。

    カレンダーは表示用でしかないので、落ちても日次バッチ全体を止めない。
    """
    try:
        return [e.to_dict() for e in fetch_events(target)]
    except Exception:
        logger.exception("カレンダーの取得に失敗した。予定なしとして続行する")
        return []
