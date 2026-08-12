"""環境変数の読み出し。

public リポジトリなので、ここで読んだ値は絶対にログへ出さないこと。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# ローカル実行のためにリポジトリ直下の .env を読む。
# override=False なので、GitHub Actions で渡される環境変数を上書きすることはない。
# Actions には .env が無いので、そこでは何も起きない。
_REPO_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(_REPO_ROOT / ".env", override=False)


# 無料プランのプロジェクト数上限のため既存プロジェクトに相乗りしている。
# 相手の public スキーマと混ざらないよう、専用スキーマを使う（docs/09-setup-supabase.md）
SCHEMA = "coach"


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
    # secret key（sb_secret_...）。Postgres の service_role ロールで動くため RLS をバイパスする。
    # 旧 service_role JWT でも動くが、2026 年末で廃止予定なので secret key を使う
    secret_key: str

    @classmethod
    def from_env(cls) -> SupabaseConfig:
        return cls(
            url=_require("SUPABASE_URL"),
            secret_key=_require("SUPABASE_SECRET_KEY"),
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


def calendar_configured() -> bool:
    """カレンダーは任意設定。未設定でもバッチは動く（予定なしとして扱う）。"""
    return bool(_optional("GOOGLE_CALENDAR_ICS_URL"))


def calendar_ics_url() -> str:
    """Google カレンダーの非公開 iCal URL。実質的な認証情報なのでログに出さない。"""
    return _require("GOOGLE_CALENDAR_ICS_URL")
