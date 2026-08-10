"""Web Push 送信。

**ペイロードにメニュー本体を載せない。**トリガーと短い要約のみを運ぶ。
本体は 03:00 のバッチで Supabase に保存済みで、PWA は起動時に必ず DB から読む。
詳細は docs/adr/0004-push-payload-minimal.md。

iOS 固有の注意:
  - silent push は不可。Service Worker の push ハンドラで必ず showNotification() を呼ぶこと
  - 404/410 が返ったら購読を DB から削除する（PWA 起動時に再購読する）
  - VAPID の sub が mailto: / https:// でないと Apple は 403 を返す
"""

from __future__ import annotations

import json
import logging
from typing import Any

from pywebpush import WebPushException, webpush

from ..config import PushConfig
from ..db import client

logger = logging.getLogger(__name__)

# ペイロードは 4KB 未満に収める。そもそも要約しか載せないので通常は問題にならない
MAX_SUMMARY_LEN = 120


def _subscriptions() -> list[dict[str, Any]]:
    res = client().table("push_subscriptions").select("*").execute()
    return res.data


def _delete_subscription(endpoint: str) -> None:
    client().table("push_subscriptions").delete().eq("endpoint", endpoint).execute()
    logger.info("失効した購読を削除した")


def send_menu_notification(title: str, summary: str, target_date: str) -> int:
    """全購読へ通知を送る。送信成功件数を返す。"""
    cfg = PushConfig.from_env()
    payload = json.dumps(
        {
            "title": title,
            "body": summary[:MAX_SUMMARY_LEN],
            "date": target_date,  # PWA はこれを見て DB から本体を読む
        },
        ensure_ascii=False,
    )

    sent = 0
    for sub in _subscriptions():
        subscription_info = {
            "endpoint": sub["endpoint"],
            "keys": {"p256dh": sub["p256dh"], "auth": sub["auth"]},
        }
        try:
            webpush(
                subscription_info=subscription_info,
                data=payload,
                vapid_private_key=cfg.vapid_private_key,
                vapid_claims={"sub": cfg.vapid_subject},
            )
            sent += 1
        except WebPushException as e:
            status = getattr(e.response, "status_code", None)
            if status in (404, 410):
                _delete_subscription(sub["endpoint"])
            else:
                # endpoint は URL だがログに出さない（購読の識別子であり漏らす必要がない）
                logger.error("push 送信に失敗した: status=%s", status)

    client().table("notifications").insert(
        {"title": title, "body": summary[:MAX_SUMMARY_LEN], "target_date": target_date}
    ).execute()

    logger.info("push を %d 件送信した", sent)
    return sent
