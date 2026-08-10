#!/usr/bin/env python
"""Garmin トークンの初期投入（ローカル専用）。

初回ログインは MFA の対話が必要なので、この操作だけはローカルで行う。
生成されたトークンを Supabase の garmin_tokens テーブルへ投入する。

    cd batch
    uv run python scripts/bootstrap_garmin_token.py

必要な環境変数: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY / GARMIN_EMAIL / GARMIN_PASSWORD
（メール・パスワードは未設定なら対話で聞く）

トークンが完全に失効してバッチが落ちたときも、これを再実行して復旧する。
"""

from __future__ import annotations

import getpass
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from garminconnect import Garmin  # noqa: E402

from personal_coach.db import GarminTokenStore  # noqa: E402
from personal_coach.garmin.auth import _dir_to_dict  # noqa: E402


def main() -> int:
    email = os.environ.get("GARMIN_EMAIL") or input("Garmin email: ")
    password = os.environ.get("GARMIN_PASSWORD") or getpass.getpass("Garmin password: ")

    with tempfile.TemporaryDirectory(prefix="garmin-bootstrap-") as tmp:
        client = Garmin(email, password, prompt_mfa=lambda: input("MFA code: "))
        client.login(tmp)

        tokens = _dir_to_dict(Path(tmp))
        if not tokens:
            print("トークンファイルが生成されなかった。garminconnect の挙動を確認すること")
            return 1

        print(f"取得したトークンファイル: {', '.join(tokens)}")
        GarminTokenStore().save(tokens)
        print("garmin_tokens に投入した")

    # 疎通確認。個人データなので中身は出さず件数だけ
    print(json.dumps({"ok": True}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
