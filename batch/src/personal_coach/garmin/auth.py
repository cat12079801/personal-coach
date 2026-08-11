"""Garmin 認証とトークンの Supabase 往復。

トークンは自動リフレッシュされるため、リフレッシュ後の値を書き戻す先が必要になる。
GitHub Actions のランナーは実行ごとに破棄されるので、Supabase の 1 行テーブルを使う。
詳細は docs/adr/0005-garmin-token-in-supabase.md。

保存形式はトークンディレクトリの「ファイル名 -> 内容」の dict。
個々のファイル名や構造を前提にしないので、garth 側の配置が変わっても壊れない。
"""

from __future__ import annotations

import json
import logging
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from garminconnect import Garmin

from ..config import GarminConfig
from ..db import GarminTokenStore

logger = logging.getLogger(__name__)


def _dir_to_dict(directory: Path) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for path in sorted(directory.iterdir()):
        if not path.is_file():
            continue
        text = path.read_text()
        try:
            out[path.name] = json.loads(text)
        except json.JSONDecodeError:
            # JSON でないトークンファイルが増えても落とさない
            out[path.name] = text
    return out


def _dict_to_dir(data: dict[str, Any], directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for name, content in data.items():
        # ファイル名は DB 由来。パス区切りが混じっても外に書かせない
        target = directory / Path(name).name
        target.write_text(content if isinstance(content, str) else json.dumps(content))


# トークンを保持しているオブジェクトの属性名。ライブラリの版によって違う。
# 0.3.x 系は Garmin.client（garminconnect.client.Client）が dump/load を持つ。
# 旧版は garth に委譲していたため、両方を順に試す。
_TOKEN_HOLDERS = ("client", "garth")


def _dump_tokens(client: Garmin, directory: Path) -> bool:
    """現在のトークン（リフレッシュ済みかもしれない）をディレクトリへ書き出す。

    書き出せないとリフレッシュ後の値を DB に戻せず、トークンはいずれ失効する。
    再取得は MFA 対話が必要で、しかも Garmin の IP レート制限に当たりやすい。
    したがって失敗は必ず ERROR で残す。バッチ自体は落とさない。
    """
    for attr in _TOKEN_HOLDERS:
        dump = getattr(getattr(client, attr, None), "dump", None)
        if not callable(dump):
            continue
        try:
            dump(str(directory))
            return True
        except Exception:
            logger.exception("%s.dump() に失敗した", attr)
    logger.error(
        "トークンをダンプできなかった。リフレッシュ後の値が DB に戻らないため、"
        "いずれ再ログインが必要になる。garminconnect の API 変更を確認すること"
    )
    return False


@contextmanager
def garmin_session(store: GarminTokenStore | None = None) -> Iterator[Garmin]:
    """ログイン済みの Garmin クライアントを返し、終了時にトークンを DB へ書き戻す。

    DB のトークンで再開できればログイン不要。失効していた場合のみ
    GARMIN_EMAIL / GARMIN_PASSWORD でのフルログインを試みる。
    ただし GitHub Actions では MFA を越えられないため、その場合は例外で落ちる。
    """
    store = store or GarminTokenStore()
    saved = store.load()

    with tempfile.TemporaryDirectory(prefix="garmin-tokens-") as tmp:
        tokendir = Path(tmp)
        if saved:
            _dict_to_dir(saved, tokendir)
        else:
            logger.info("DB にトークンがない。フルログインを試みる")

        cfg = GarminConfig.from_env()
        client = Garmin(cfg.email, cfg.password)
        client.login(str(tokendir))

        try:
            yield client
        finally:
            _dump_tokens(client, tokendir)
            current = _dir_to_dict(tokendir)
            if current and current != saved:
                store.save(current)
                logger.info("リフレッシュされたトークンを DB に書き戻した")
