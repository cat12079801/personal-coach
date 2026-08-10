"""Supabase クライアント。バッチは service_role キーで RLS をバイパスする。"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from supabase import Client, create_client

from .config import SupabaseConfig


@lru_cache(maxsize=1)
def client() -> Client:
    cfg = SupabaseConfig.from_env()
    return create_client(cfg.url, cfg.service_role_key)


class GarminTokenStore:
    """`garmin_tokens` テーブル（1 行）との読み書き。

    保存形式はトークンディレクトリの「ファイル名 -> 内容」の dict。
    garth 側のファイル構成が変わっても実装を直さずに済む。
    詳細は docs/adr/0005-garmin-token-in-supabase.md を参照。
    """

    ROW_ID = 1

    def load(self) -> dict[str, Any] | None:
        res = client().table("garmin_tokens").select("token_json").eq("id", self.ROW_ID).execute()
        if not res.data:
            return None
        return res.data[0]["token_json"]

    def save(self, token_json: dict[str, Any]) -> None:
        client().table("garmin_tokens").upsert(
            {"id": self.ROW_ID, "token_json": token_json}
        ).execute()


def known_activity_ids() -> set[str]:
    """差分同期の打ち切り判定に使う既知の Garmin activityId 集合。"""
    res = client().table("activities").select("garmin_activity_id").execute()
    return {row["garmin_activity_id"] for row in res.data}
