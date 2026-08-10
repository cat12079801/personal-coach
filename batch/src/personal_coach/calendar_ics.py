"""Google カレンダーの非公開 iCal URL を読む。

OAuth もサービスアカウントも使わない（docs/adr/0003-ical-instead-of-oauth.md）。

注意: この .ics は Google 側でキャッシュされ、反映が数時間遅れることがある。
前夜遅くに追加された予定を 03:00 のバッチが拾えない可能性があるため、
アプリ側の「メニュー再生成」ボタンでの手動リカバリとセットで運用する。
"""

from __future__ import annotations

import datetime as dt
import logging
from dataclasses import dataclass

import requests
from icalendar import Calendar

from .config import calendar_ics_url

logger = logging.getLogger(__name__)

TIMEOUT_SEC = 30


@dataclass(frozen=True)
class Event:
    summary: str
    start: dt.datetime | dt.date
    end: dt.datetime | dt.date | None

    @property
    def date(self) -> dt.date:
        return self.start.date() if isinstance(self.start, dt.datetime) else self.start


def fetch_events(target: dt.date) -> list[Event]:
    """指定日の予定を返す。

    繰り返し予定の展開はしていない。スケート予定が繰り返し登録される運用になったら
    `recurring-ical-events` の導入を検討する。
    """
    # URL は認証情報相当。例外メッセージにも載せない
    try:
        res = requests.get(calendar_ics_url(), timeout=TIMEOUT_SEC)
        res.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"カレンダーの取得に失敗した: {type(e).__name__}") from None

    events: list[Event] = []
    for component in Calendar.from_ical(res.content).walk("VEVENT"):
        start = component.get("DTSTART").dt
        end_prop = component.get("DTEND")
        event = Event(
            summary=str(component.get("SUMMARY", "")),
            start=start,
            end=end_prop.dt if end_prop else None,
        )
        if event.date == target:
            events.append(event)

    logger.info("%s の予定 %d 件", target, len(events))
    return events


SKATING_KEYWORDS = ("スケート", "リンク", "skat")


def has_skating(target: dt.date, keywords: tuple[str, ...] = SKATING_KEYWORDS) -> bool:
    """指定日にスケートの予定があるか。判定キーワードは運用しながら調整する。"""
    return any(any(k.lower() in e.summary.lower() for k in keywords) for e in fetch_events(target))
