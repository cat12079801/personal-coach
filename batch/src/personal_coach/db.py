"""Supabase クライアント。

バッチは secret key（`sb_secret_...`）で接続する。これは Postgres の service_role ロールに
対応し、BYPASSRLS 属性を持つので RLS を素通りする。フロントの publishable key とは別物。
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from supabase import Client, ClientOptions, create_client

from .config import SCHEMA, SupabaseConfig


@lru_cache(maxsize=1)
def client() -> Client:
    cfg = SupabaseConfig.from_env()
    # 既存プロジェクトに相乗りしているので、専用スキーマを明示する。
    # これを忘れると相手の public スキーマを見に行って 404 になる
    return create_client(cfg.url, cfg.secret_key, options=ClientOptions(schema=SCHEMA))


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
