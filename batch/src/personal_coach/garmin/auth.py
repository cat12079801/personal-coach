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


def _dump_tokens(client: Garmin, directory: Path) -> None:
    """現在のトークン（リフレッシュ済みかもしれない）をディレクトリへ書き出す。

    garth の API は変わりうるので、失敗しても致命傷にしない。
    次回 DB のトークンが古くてもフルログインにフォールバックできる。
    """
    try:
        client.garth.dump(str(directory))
    except Exception:  # noqa: BLE001 - ライブラリ側の変更を握りつぶして継続する
        logger.warning("トークンのダンプに失敗した。garminconnect の API 変更を確認すること")


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
