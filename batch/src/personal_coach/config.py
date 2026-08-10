"""環境変数の読み出し。

public リポジトリなので、ここで読んだ値は絶対にログへ出さないこと。
"""

from __future__ import annotations

import os
from dataclasses import dataclass


class ConfigError(RuntimeError):
    pass


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ConfigError(f"環境変数 {name} が設定されていない")
    return value


def _optional(name: str) -> str | None:
    return os.environ.get(name) or None


@dataclass(frozen=True)
class SupabaseConfig:
    url: str
    service_role_key: str

    @classmethod
    def from_env(cls) -> SupabaseConfig:
        return cls(
            url=_require("SUPABASE_URL"),
            service_role_key=_require("SUPABASE_SERVICE_ROLE_KEY"),
        )


@dataclass(frozen=True)
class GarminConfig:
    """email / password はトークン失効時の再ログインにのみ使う。

    通常運用では Supabase に保存されたトークンだけでログインできる。
    """

    email: str | None
    password: str | None

    @classmethod
    def from_env(cls) -> GarminConfig:
        return cls(email=_optional("GARMIN_EMAIL"), password=_optional("GARMIN_PASSWORD"))


@dataclass(frozen=True)
class PushConfig:
    vapid_public_key: str
    vapid_private_key: str
    # mailto:... または https://... でなければ Apple のプッシュサービスは 403 を返す
    vapid_subject: str

    @classmethod
    def from_env(cls) -> PushConfig:
        subject = _require("VAPID_SUBJECT")
        if not subject.startswith(("mailto:", "https://")):
            raise ConfigError("VAPID_SUBJECT は mailto: または https:// で始まる必要がある")
        return cls(
            vapid_public_key=_require("VAPID_PUBLIC_KEY"),
            vapid_private_key=_require("VAPID_PRIVATE_KEY"),
            vapid_subject=subject,
        )


def calendar_ics_url() -> str:
    """Google カレンダーの非公開 iCal URL。実質的な認証情報なのでログに出さない。"""
    return _require("GOOGLE_CALENDAR_ICS_URL")
